import sqlite3
import json
import os
import threading
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("edge.storage.outbox")

DEFAULT_DB_PATH = os.environ.get(
    "OUTBOX_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "outbox.db")
)


class OutboxRepository:
    """
    Thread-safe SQLite outbox repository implementing local queuing,
    idempotent event storage, and atomic state transitions for offline-first resilience.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a thread-safe SQLite connection with WAL mode and row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging (WAL) for high concurrency and robust lock handling
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initializes the outbox table and indexes if they do not exist."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS outbox (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE NOT NULL,
                        payload TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PENDING',
                        attempt_count INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_outbox_status_id ON outbox(status, id);
                """)
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_event_id ON outbox(event_id);
                """)
                conn.commit()

        # Recover any events left in PROCESSING state from previous crashes
        self.recover_stale_processing()

    def enqueue(self, event_id: str, payload: Any) -> bool:
        """
        Inserts event as PENDING into the outbox.
        Safe against duplicate event_id (idempotent insert).
        Returns True if newly inserted, False if duplicate already exists.
        """
        if isinstance(payload, (dict, list)):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO outbox (event_id, payload, status, attempt_count, created_at, updated_at)
                        VALUES (?, ?, 'PENDING', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (event_id, payload_str)
                    )
                    conn.commit()
                    inserted = cursor.rowcount > 0
                    if inserted:
                        logger.debug(f"Outbox: Enqueued event {event_id} as PENDING.")
                    else:
                        logger.debug(f"Outbox: Duplicate event {event_id} ignored.")
                    return inserted
            except Exception as e:
                logger.error(f"Outbox: Failed to enqueue event {event_id}: {e}")
                raise

    def fetch_pending_batch(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves PENDING records ready for transmission, ordered by oldest first.
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, event_id, payload, status, attempt_count, last_error, created_at, updated_at
                    FROM outbox
                    WHERE status = 'PENDING'
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (limit,)
                )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    try:
                        parsed_payload = json.loads(row["payload"])
                    except Exception:
                        parsed_payload = row["payload"]

                    results.append({
                        "id": row["id"],
                        "event_id": row["event_id"],
                        "payload": parsed_payload,
                        "status": row["status"],
                        "attempt_count": row["attempt_count"],
                        "last_error": row["last_error"],
                        "created_at": str(row["created_at"]),
                        "updated_at": str(row["updated_at"]),
                    })
                return results

    def mark_processing(self, ids: List[int]) -> None:
        """
        Atomically transitions records from PENDING to PROCESSING.
        """
        if not ids:
            return

        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    f"""
                    UPDATE outbox
                    SET status = 'PROCESSING',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                    """,
                    ids
                )
                conn.commit()
                logger.debug(f"Outbox: Marked {len(ids)} record(s) as PROCESSING.")

    def mark_sent(self, record_id: int) -> None:
        """
        Marks an outbox record as SENT upon confirmed cloud delivery.
        """
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE outbox
                    SET status = 'SENT',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (record_id,)
                )
                conn.commit()
                logger.debug(f"Outbox: Record {record_id} marked as SENT.")

    def record_failure(self, record_id: int, error_message: str, max_attempts: int = 5) -> None:
        """
        Increments attempt_count and updates last_error.
        If attempt_count >= max_attempts, marks record as FAILED.
        Otherwise, resets status back to PENDING for subsequent retry.
        """
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE outbox
                    SET attempt_count = attempt_count + 1,
                        last_error = ?,
                        status = CASE WHEN attempt_count + 1 >= ? THEN 'FAILED' ELSE 'PENDING' END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (error_message, max_attempts, record_id)
                )
                conn.commit()
                logger.warning(
                    f"Outbox: Recorded failure for record {record_id}. Error: {error_message}"
                )

    def recover_stale_processing(self) -> int:
        """
        Resets any records stuck in PROCESSING back to PENDING (e.g. after service restart).
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE outbox
                    SET status = 'PENDING',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE status = 'PROCESSING'
                    """
                )
                conn.commit()
                count = cursor.rowcount
                if count > 0:
                    logger.info(f"Outbox: Recovered {count} stale PROCESSING records back to PENDING.")
                return count

    def get_stats(self) -> Dict[str, int]:
        """Returns count of outbox records grouped by status."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT status, count(*) as count
                    FROM outbox
                    GROUP BY status
                    """
                )
                return {row["status"]: row["count"] for row in cursor.fetchall()}


# Global singleton repository
outbox_repo = OutboxRepository()
