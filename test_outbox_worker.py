import sys
import os
import asyncio
import threading
import tempfile
sys.path.insert(0, "services/edge")

import httpx
from app.storage.outbox import OutboxRepository
from app.sync.worker import SyncWorker
from app.sync.http_client import CloudApiClient

async def run_tests():
    # 1. OutboxRepository tests
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as wtf:
        worker_db = wtf.name

    try:
        print("=== 1. Testing OutboxRepository Schema & Operations ===")
        repo = OutboxRepository(db_path=temp_db)

        # 1a. Enqueue
        evt1 = "evt-001"
        payload1 = {"temperature": 25.5, "humidity": 60.0}
        inserted = repo.enqueue(evt1, payload1)
        assert inserted is True, "First enqueue should succeed"

        # 1b. Duplicate Enqueue
        inserted_dup = repo.enqueue(evt1, payload1)
        assert inserted_dup is False, "Duplicate enqueue should be ignored"

        # 1c. Fetch Pending Batch
        batch = repo.fetch_pending_batch(limit=10)
        assert len(batch) == 1
        assert batch[0]["event_id"] == evt1
        assert batch[0]["status"] == "PENDING"
        assert batch[0]["attempt_count"] == 0
        assert batch[0]["payload"]["temperature"] == 25.5
        record_id = batch[0]["id"]

        # 1d. Mark Processing
        repo.mark_processing([record_id])
        batch_after_proc = repo.fetch_pending_batch(limit=10)
        assert len(batch_after_proc) == 0, "No pending items should be returned while PROCESSING"

        # 1e. Record Failure (attempt 1 -> resets to PENDING)
        repo.record_failure(record_id, "Simulated timeout", max_attempts=3)
        batch_after_fail = repo.fetch_pending_batch(limit=10)
        assert len(batch_after_fail) == 1
        assert batch_after_fail[0]["status"] == "PENDING"
        assert batch_after_fail[0]["attempt_count"] == 1
        assert batch_after_fail[0]["last_error"] == "Simulated timeout"

        # 1f. Record Failure until max_attempts -> FAILED
        repo.record_failure(record_id, "Error 2", max_attempts=3) # count = 2 -> PENDING
        repo.record_failure(record_id, "Error 3", max_attempts=3) # count = 3 >= 3 -> FAILED
        batch_after_max = repo.fetch_pending_batch(limit=10)
        assert len(batch_after_max) == 0, "Item should not be PENDING once FAILED"

        # 1g. Mark Sent
        evt2 = "evt-002"
        repo.enqueue(evt2, {"temperature": 30.0})
        b2 = repo.fetch_pending_batch(limit=10)
        id2 = b2[0]["id"]
        repo.mark_sent(id2)
        stats = repo.get_stats()
        print("Outbox Stats:", stats)
        assert stats.get("SENT") == 1
        assert stats.get("FAILED") == 1
        print("OutboxRepository CRUD and state machine verified successfully!")

        print("\n=== 2. Testing Thread-Safe Concurrent Enqueues ===")
        def concurrent_writer(thread_idx, count=25):
            for i in range(count):
                repo.enqueue(f"evt-t{thread_idx}-{i}", {"val": i})

        threads = [threading.Thread(target=concurrent_writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        all_pending = repo.fetch_pending_batch(limit=200)
        assert len(all_pending) == 100, f"Expected 100 concurrently enqueued events, found {len(all_pending)}"
        print(f"Concurrent stress test passed! Successfully enqueued {len(all_pending)} events without locks.")

        print("\n=== 3. Testing SyncWorker with Exponential Backoff ===")
        class MockTransport(httpx.AsyncBaseTransport, httpx.BaseTransport):
            def __init__(self):
                self.should_fail = False
                self.fail_count = 0
                self.success_count = 0

            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                url = str(request.url)
                if "/api/v1/auth/login" in url:
                    return httpx.Response(200, json={"data": {"token": "valid-jwt"}}, request=request)
                if "/api/v1/telemetry" in url:
                    if self.should_fail:
                        self.fail_count += 1
                        return httpx.Response(500, json={"error": {"message": "Cloud internal error"}}, request=request)
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
            max_backoff=1.0,
            idle_poll_interval=0.05
        )

        # Enqueue 2 events
        worker_repo.enqueue("evt-w1", {"temp": 20})
        worker_repo.enqueue("evt-w2", {"temp": 21})

        # Start worker
        worker.start()
        await asyncio.sleep(0.3)

        w_stats = worker_repo.get_stats()
        print("Worker Stats after success:", w_stats)
        assert w_stats.get("SENT") == 2, f"Expected 2 events SENT, got {w_stats}"

        # Now test failure and exponential backoff
        mock_transport.should_fail = True
        worker_repo.enqueue("evt-w3", {"temp": 22})
        await asyncio.sleep(0.4)

        w_stats_fail = worker_repo.get_stats()
        print("Worker Stats after failure:", w_stats_fail)
        assert mock_transport.fail_count > 0, "Expected failures to be recorded"
        assert worker._backoff_delay > 0.2, "Expected backoff delay to increase exponentially"
        print(f"Exponential backoff verified! Current delay: {worker._backoff_delay:.2f}s")

        # Stop worker cleanly
        await worker.stop()
        print("SyncWorker stopped cleanly.")

        httpx.AsyncClient = orig_async
        print("\nAll Outbox & SyncWorker tests passed successfully!")

    finally:
        for p in [temp_db, worker_db]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

if __name__ == "__main__":
    asyncio.run(run_tests())
