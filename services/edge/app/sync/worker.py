import asyncio
import logging
import httpx
from typing import Optional, Callable
from app.storage.outbox import outbox_repo, OutboxRepository
from app.sync.http_client import cloud_client, CloudApiClient, CloudConnectionError, CloudAuthenticationError

logger = logging.getLogger("edge.sync.worker")


class SyncWorker:
    """
    Asynchronous background worker that pulls pending batches from the SQLite outbox,
    transmits them to the Cloud API with Bearer token authentication,
    and applies exponential backoff on cloud/network failure to prevent aggressive retries.
    """

    def __init__(
        self,
        repository: Optional[OutboxRepository] = None,
        client: Optional[CloudApiClient] = None,
        batch_size: int = 20,
        initial_backoff: float = 2.0,
        max_backoff: float = 30.0,
        idle_poll_interval: float = 1.0,
        is_offline_func: Optional[Callable[[], bool]] = None,
    ):
        self.repo = repository or outbox_repo
        self.client = client or cloud_client
        self.batch_size = batch_size
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.idle_poll_interval = idle_poll_interval
        self.is_offline_func = is_offline_func

        self._backoff_delay = self.initial_backoff
        self._is_running = False
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    def start(self) -> asyncio.Task:
        """Starts the sync worker as a background asyncio Task."""
        if self._is_running and self._task and not self._task.done():
            return self._task

        self._is_running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="sync_worker_loop")
        logger.info("SyncWorker: Background sync loop started.")
        return self._task

    async def stop(self) -> None:
        """Signals the sync worker to stop gracefully."""
        if not self._is_running:
            return

        logger.info("SyncWorker: Stopping background sync worker...")
        self._is_running = False
        self._stop_event.set()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("SyncWorker: Stopped cleanly.")

    async def _run_loop(self) -> None:
        """Main asynchronous processing loop with exponential backoff on failures."""
        # On startup, recover any records stuck in PROCESSING from a prior crash
        self.repo.recover_stale_processing()

        while self._is_running and not self._stop_event.is_set():
            try:
                # Check simulated offline fault injection if configured
                if self.is_offline_func and self.is_offline_func():
                    logger.debug("SyncWorker: Simulated offline fault active. Pausing sync.")
                    await asyncio.sleep(self.idle_poll_interval)
                    continue

                # 1. Fetch pending batch
                batch = self.repo.fetch_pending_batch(limit=self.batch_size)
                if not batch:
                    # Nothing to send, idle poll
                    await asyncio.sleep(self.idle_poll_interval)
                    continue

                batch_ids = [item["id"] for item in batch]
                logger.info(f"SyncWorker: Fetched {len(batch)} pending event(s) from outbox.")

                # 2. Mark batch as PROCESSING
                self.repo.mark_processing(batch_ids)

                # 3. Process each item in batch
                network_failure = False
                unprocessed_ids = []

                for index, item in enumerate(batch):
                    if not self._is_running or self._stop_event.is_set():
                        unprocessed_ids.extend(batch_ids[index:])
                        break

                    record_id = item["id"]
                    event_id = item["event_id"]
                    payload = item["payload"]

                    # Ensure eventId is present in payload for idempotency
                    if isinstance(payload, dict) and "eventId" not in payload:
                        payload["eventId"] = event_id

                    try:
                        resp = await self.client.post_telemetry_async(payload, timeout=5.0)

                        if resp.status_code in (200, 201):
                            self.repo.mark_sent(record_id)
                            logger.info(f"SyncWorker: Successfully synced event {event_id} (ID: {record_id}).")
                            # Successful transmission resets backoff
                            self._backoff_delay = self.initial_backoff
                        elif resp.status_code >= 500:
                            err_msg = f"Cloud API server error: HTTP {resp.status_code}"
                            self.repo.record_failure(record_id, err_msg, max_attempts=5)
                            network_failure = True
                            unprocessed_ids.extend(batch_ids[index + 1:])
                            break
                        else:
                            # 4xx Client error (e.g. 422 Unprocessable Entity)
                            err_msg = f"Cloud API rejected telemetry: HTTP {resp.status_code} - {resp.text}"
                            self.repo.record_failure(record_id, err_msg, max_attempts=5)

                    except (CloudConnectionError, CloudAuthenticationError, httpx.RequestError) as exc:
                        err_msg = f"Connection error: {exc}"
                        self.repo.record_failure(record_id, err_msg, max_attempts=5)
                        network_failure = True
                        unprocessed_ids.extend(batch_ids[index + 1:])
                        break
                    except Exception as exc:
                        err_msg = f"Unexpected error during sync: {exc}"
                        self.repo.record_failure(record_id, err_msg, max_attempts=5)

                # Reset any unattempted items in this batch back to PENDING so they don't get stuck
                if unprocessed_ids:
                    with self.repo._lock:
                        with self.repo._get_connection() as conn:
                            placeholders = ",".join("?" for _ in unprocessed_ids)
                            conn.execute(
                                f"UPDATE outbox SET status = 'PENDING' WHERE id IN ({placeholders}) AND status = 'PROCESSING'",
                                unprocessed_ids
                            )
                            conn.commit()

                # 4. Handle Exponential Backoff on network / 5xx failures
                if network_failure:
                    logger.warning(
                        f"SyncWorker: Cloud failure detected. Backing off for {self._backoff_delay:.1f}s before retry..."
                    )
                    await asyncio.sleep(self._backoff_delay)
                    # Exponential increase capped at max_backoff (e.g., 2s -> 4s -> 8s -> 16s -> 30s)
                    self._backoff_delay = min(self._backoff_delay * 2, self.max_backoff)

            except asyncio.CancelledError:
                logger.info("SyncWorker: Task cancelled during execution.")
                break
            except Exception as e:
                logger.error(f"SyncWorker: Unexpected error in run loop: {e}", exc_info=True)
                await asyncio.sleep(self.idle_poll_interval)


# Global singleton worker
sync_worker = SyncWorker()
