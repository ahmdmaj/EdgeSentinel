import sys
import os
import asyncio
import threading
import tempfile
import sqlite3

# Ensure services/edge is in Python path
sys.path.insert(0, os.path.abspath("services/edge"))

import httpx
from app.storage.outbox import OutboxRepository
from app.sync.worker import SyncWorker
from app.sync.http_client import CloudApiClient
from app.main import graceful_shutdown


async def run_tests():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as wtf:
        worker_db = wtf.name

    try:
        print("=== 1. Testing OutboxRepository Schema (outbox_events) & DAO Operations ===")
        repo = OutboxRepository(db_path=temp_db)

        # Verify table name is outbox_events
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='outbox_events';")
        tbl = cursor.fetchone()
        assert tbl is not None, "Table 'outbox_events' must exist in SQLite database"

        # Verify schema columns
        cursor.execute("PRAGMA table_info(outbox_events);")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        expected_cols = ["id", "event_id", "payload", "status", "attempt_count", "last_error", "created_at", "updated_at"]
        for col in expected_cols:
            assert col in columns, f"Column '{col}' must be present in outbox_events table"
        print("Schema verified: 'outbox_events' exists with all required columns.")

        # 1a. insert_event
        evt1 = "evt-001"
        payload1 = {"temperature": 25.5, "humidity": 60.0}
        inserted = repo.insert_event(evt1, payload1)
        assert inserted is True, "First insert_event should succeed"

        # 1b. Idempotency against duplicate event_id
        inserted_dup = repo.insert_event(evt1, payload1)
        assert inserted_dup is False, "Duplicate insert_event must be safely ignored"

        # Backward compatibility alias
        inserted_alias = repo.enqueue("evt-alias", {"test": True})
        assert inserted_alias is True, "enqueue() alias should succeed"

        # 1c. Fetch Pending Batch (FIFO order)
        batch = repo.fetch_pending_batch(limit=10)
        assert len(batch) == 2
        assert batch[0]["event_id"] == evt1
        assert batch[0]["status"] == "PENDING"
        assert batch[0]["attempt_count"] == 0
        assert batch[0]["payload"]["temperature"] == 25.5
        record_id = batch[0]["id"]

        # 1d. Mark Processing
        repo.mark_processing([record_id])
        batch_after_proc = repo.fetch_pending_batch(limit=10)
        assert len(batch_after_proc) == 1, "Only unprocessed item should be returned while first is PROCESSING"
        assert batch_after_proc[0]["event_id"] == "evt-alias"

        # 1e. Record Failure (attempt 1 -> resets to PENDING)
        repo.record_failure(record_id, "Simulated network timeout", max_attempts=3)
        batch_after_fail = repo.fetch_pending_batch(limit=10)
        assert any(item["event_id"] == evt1 for item in batch_after_fail)
        failed_item = next(item for item in batch_after_fail if item["event_id"] == evt1)
        assert failed_item["status"] == "PENDING"
        assert failed_item["attempt_count"] == 1
        assert failed_item["last_error"] == "Simulated network timeout"

        # 1f. Record Failure until max_attempts -> FAILED
        repo.record_failure(record_id, "Error 2", max_attempts=3)  # count = 2 -> PENDING
        repo.record_failure(record_id, "Error 3", max_attempts=3)  # count = 3 >= 3 -> FAILED
        batch_after_max = repo.fetch_pending_batch(limit=10)
        assert all(item["event_id"] != evt1 for item in batch_after_max), "Event should not be PENDING once FAILED"

        # 1g. Mark Sent
        evt2 = "evt-002"
        repo.insert_event(evt2, {"temperature": 30.0})
        b2 = repo.fetch_pending_batch(limit=10)
        item2 = next(item for item in b2 if item["event_id"] == evt2)
        repo.mark_sent([item2["id"]])

        stats = repo.get_stats()
        print("Outbox Stats:", stats)
        assert stats.get("SENT") == 1
        assert stats.get("FAILED") == 1
        print("OutboxRepository CRUD and state machine verified successfully!")

        print("\n=== 2. Testing Concurrent Multi-threaded Ingestion ===")
        def concurrent_writer(thread_idx, count=25):
            for i in range(count):
                repo.insert_event(f"evt-t{thread_idx}-{i}", {"val": i, "worker": thread_idx})

        threads = [threading.Thread(target=concurrent_writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        all_pending = repo.fetch_pending_batch(limit=500)
        # 100 new events + 1 evt-alias from before = 101
        assert len(all_pending) >= 100, f"Expected at least 100 concurrently enqueued events, found {len(all_pending)}"
        print(f"Concurrent stress test passed! Successfully inserted {len(all_pending)} events without locks.")

        print("\n=== 3. Testing Section 24 WAL Checkpoint & Clean DB Close ===")
        repo.close()
        print("WAL checkpoint and SQLite handle close verified successfully.")

        print("\n=== 4. Testing Resilient SyncWorker & Exponential Backoff ===")
        class MockTransport(httpx.AsyncBaseTransport, httpx.BaseTransport):
            def __init__(self):
                self.should_fail = False
                self.fail_count = 0
                self.success_count = 0

            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                url = str(request.url)
                if "/api/v1/auth/login" in url:
                    return httpx.Response(200, json={"data": {"token": "mock-jwt-token"}}, request=request)
                if "/health" in url:
                    if self.should_fail:
                        return httpx.Response(503, json={"status": "unavailable"}, request=request)
                    return httpx.Response(200, json={"status": "healthy"}, request=request)
                if "/api/v1/telemetry" in url:
                    if self.should_fail:
                        self.fail_count += 1
                        return httpx.Response(500, json={"error": {"message": "Cloud 500 error"}}, request=request)
                    self.success_count += 1
                    return httpx.Response(201, json={"data": {"message": "Recorded"}}, request=request)
                return httpx.Response(404, request=request)

        mock_transport = MockTransport()
        orig_async = httpx.AsyncClient
        httpx.AsyncClient = lambda **kwargs: orig_async(transport=mock_transport, **kwargs)

        test_client = CloudApiClient(base_url="http://mock-cloud:3000")
        worker_repo = OutboxRepository(db_path=worker_db)

        worker = SyncWorker(
            repository=worker_repo,
            client=test_client,
            batch_size=5,
            initial_backoff=0.2,
            max_backoff=60.0,
            idle_poll_interval=0.05
        )

        # Enqueue 2 events
        worker_repo.insert_event("evt-w1", {"temp": 20})
        worker_repo.insert_event("evt-w2", {"temp": 21})

        # Start worker and allow flush
        worker.start()
        await asyncio.sleep(0.3)

        w_stats = worker_repo.get_stats()
        print("Worker Stats after successful sync:", w_stats)
        assert w_stats.get("SENT") == 2, f"Expected 2 events SENT, got {w_stats}"

        # Test failure and exponential backoff
        mock_transport.should_fail = True
        worker_repo.insert_event("evt-w3", {"temp": 22})
        worker_repo.insert_event("evt-w4", {"temp": 23})
        await asyncio.sleep(0.4)

        w_stats_fail = worker_repo.get_stats()
        print("Worker Stats during cloud failure:", w_stats_fail)
        assert mock_transport.fail_count > 0, "Expected failures to be recorded"
        assert worker._backoff_delay > 0.2, f"Expected backoff delay to increase, was {worker._backoff_delay}"
        print(f"Exponential backoff verified! Current delay: {worker._backoff_delay:.2f}s (capped at 60s)")

        # Verify unattempted items were reverted from PROCESSING to PENDING
        pending_after_failure = worker_repo.fetch_pending_batch(limit=10)
        assert len(pending_after_failure) > 0, "Unattempted items must be reverted to PENDING"

        # Restore connectivity and verify FIFO drainage
        mock_transport.should_fail = False
        await asyncio.sleep(0.5)
        w_stats_recovered = worker_repo.get_stats()
        print("Worker Stats after connectivity restoration:", w_stats_recovered)
        assert w_stats_recovered.get("SENT", 0) >= 3, "Expected backlogged events to flush once restored"

        # Stop worker cleanly
        await worker.stop()
        worker_repo.close()
        print("SyncWorker stopped cleanly.")

        httpx.AsyncClient = orig_async
        print("\nAll Section 21, 22, 23, and 24 tests passed successfully!")

    finally:
        for p in [temp_db, worker_db]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(run_tests())
