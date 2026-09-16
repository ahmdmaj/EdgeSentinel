import sqlite3
import json
import os
import threading
import logging
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger("edge.storage.outbox")

DEFAULT_DB_PATH = os.environ.get(
    "OUTBOX_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "outbox.db")
)


class OutboxRepository:
    """
    Thread-safe SQLite outbox repository implementing local queuing,
    idempotent event storage, and atomic state transitions for offline-first resilience.
    Uses SQLite BEGIN IMMEDIATE transactions and Write-Ahead Logging (WAL).
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Creates a thread-safe SQLite connection with WAL mode and row factory.
        Sets isolation_level=None for explicit BEGIN IMMEDIATE transaction control.
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None  # Enable explicit transaction control
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initializes the outbox_events table and handles legacy migrations."""
        with self._lock:
            conn = self._get_connection()
            try:
                # 1. Create outbox_events table according to Section 22 specification
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS outbox_events (
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
                    CREATE INDEX IF NOT EXISTS idx_outbox_events_status_id ON outbox_events(status, id);
                """)
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_events_event_id ON outbox_events(event_id);
                """)

                # 2. Check if legacy 'outbox' table exists and migrate any un-migrated records
                legacy_table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='outbox';"
                ).fetchone()
                if legacy_table:
                    conn.execute("""
                        INSERT OR IGNORE INTO outbox_events (event_id, payload, status, attempt_count, last_error, created_at, updated_at)
                        SELECT event_id, payload, status, attempt_count, last_error, created_at, updated_at
                        FROM outbox;
                    """)
                    logger.info("Outbox: Migrated legacy records from 'outbox' to 'outbox_events'.")
            finally:
                conn.close()

        # Recover any events left in PROCESSING state from previous unexpected halts
        self.recover_stale_processing()

    def insert_event(self, event_id: str, payload: Any) -> bool:
        """
        Inserts an event into outbox_events with status PENDING.
        Uses BEGIN IMMEDIATE transaction for ACID safety across concurrent threads.
        Idempotent: returns True if newly inserted, False if duplicate event_id already exists.
        """
        if isinstance(payload, (dict, list)):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO outbox_events (event_id, payload, status, attempt_count, created_at, updated_at)
                    VALUES (?, ?, 'PENDING', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                    """,
                    (event_id, payload_str)
                )
                inserted = cursor.rowcount > 0
                conn.execute("COMMIT;")
                if inserted:
                    logger.debug(f"Outbox: Inserted event {event_id} as PENDING.")
                else:
                    logger.debug(f"Outbox: Duplicate event {event_id} ignored.")
                return inserted
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                logger.error(f"Outbox: Failed to insert event {event_id}: {e}")
                raise
            finally:
                conn.close()

    # Backward-compatible alias
    enqueue = insert_event

    def fetch_pending_batch(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves oldest PENDING records ready for transmission in FIFO order (Section 22).
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT id, event_id, payload, status, attempt_count, last_error, created_at, updated_at
                    FROM outbox_events
                    WHERE status = 'PENDING'
                    ORDER BY id ASC
                    LIMIT ?;
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
            finally:
                conn.close()

    def mark_processing(self, event_ids: Union[int, str, List[Union[int, str]]]) -> None:
        """
        Atomically transitions records from PENDING to PROCESSING using BEGIN IMMEDIATE.
        Accepts either primary key integer IDs or event_id strings.
        """
        if not event_ids:
            return

        if not isinstance(event_ids, list):
            event_ids = [event_ids]

        if not event_ids:
            return

        # Determine if ids are integer PKs or string event_ids
        is_int_ids = isinstance(event_ids[0], int)
        id_column = "id" if is_int_ids else "event_id"

        placeholders = ",".join("?" for _ in event_ids)
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    f"""
                    UPDATE outbox_events
                    SET status = 'PROCESSING',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE {id_column} IN ({placeholders});
                    """,
                    event_ids
                )
                conn.execute("COMMIT;")
                logger.debug(f"Outbox: Marked {len(event_ids)} record(s) as PROCESSING.")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                logger.error(f"Outbox: Failed to mark records as PROCESSING: {e}")
                raise
            finally:
                conn.close()

    def mark_sent(self, event_ids: Union[int, str, List[Union[int, str]]]) -> None:
        """
        Atomically marks outbox records as SENT upon confirmed cloud delivery.
        Accepts either primary key integer IDs or event_id strings.
        """
        if not event_ids:
            return

        if not isinstance(event_ids, list):
            event_ids = [event_ids]

        if not event_ids:
            return

        is_int_ids = isinstance(event_ids[0], int)
        id_column = "id" if is_int_ids else "event_id"

        placeholders = ",".join("?" for _ in event_ids)
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    f"""
                    UPDATE outbox_events
                    SET status = 'SENT',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE {id_column} IN ({placeholders});
                    """,
                    event_ids
                )
                conn.execute("COMMIT;")
                logger.debug(f"Outbox: Marked {len(event_ids)} record(s) as SENT.")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                logger.error(f"Outbox: Failed to mark records as SENT: {e}")
                raise
            finally:
                conn.close()

    def record_failure(
        self,
        event_id: Union[int, str],
        error_message: str,
        max_attempts: int = 5
    ) -> None:
        """
        Increments attempt_count and updates last_error.
        If attempt_count >= max_attempts, marks record as FAILED.
        Otherwise, resets status back to PENDING for subsequent retry.
        Uses BEGIN IMMEDIATE transaction.
        """
        id_column = "id" if isinstance(event_id, int) else "event_id"

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    f"""
                    UPDATE outbox_events
                    SET attempt_count = attempt_count + 1,
                        last_error = ?,
                        status = CASE WHEN attempt_count + 1 >= ? THEN 'FAILED' ELSE 'PENDING' END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE {id_column} = ?;
                    """,
                    (error_message, max_attempts, event_id)
                )
                conn.execute("COMMIT;")
                logger.warning(
                    f"Outbox: Recorded failure for event {event_id}. Error: {error_message}"
                )
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                logger.error(f"Outbox: Failed to record failure for {event_id}: {e}")
                raise
            finally:
                conn.close()

    def recover_stale_processing(self) -> int:
        """
        Resets any records stuck in PROCESSING back to PENDING (e.g., after service restart).
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                cursor = conn.execute(
                    """
                    UPDATE outbox_events
                    SET status = 'PENDING',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE status = 'PROCESSING';
                    """
                )
                count = cursor.rowcount
                conn.execute("COMMIT;")
                if count > 0:
                    logger.info(f"Outbox: Recovered {count} stale PROCESSING records back to PENDING.")
                return count
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                logger.error(f"Outbox: Error during stale processing recovery: {e}")
                return 0
            finally:
                conn.close()

    def get_stats(self) -> Dict[str, int]:
        """Returns counts of outbox records grouped by status."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT status, count(*) as count
                    FROM outbox_events
                    GROUP BY status;
                    """
                )
                return {row["status"]: row["count"] for row in cursor.fetchall()}
            finally:
                conn.close()

    def close(self) -> None:
        """
        Graceful shutdown hook (Section 24):
        Safely checkpoints the Write-Ahead Log (WAL) to flush all in-flight writes
        to the primary database file and releases SQLite handles.
        """
        with self._lock:
            try:
                conn = self._get_connection()
                try:
                    logger.info("Outbox: Performing SQLite WAL checkpoint (TRUNCATE)...")
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    logger.info("Outbox: WAL flushed and SQLite handles cleanly closed.")
                finally:
                    conn.close()
            except Exception as e:
                logger.warning(f"Outbox: Error during SQLite WAL checkpoint close: {e}")


# Global singleton repository
outbox_repo = OutboxRepository()
