import asyncio
import httpx
import json
import logging
from storage import SessionLocal, OutboxEvent
from app.sync.http_client import cloud_client, CloudConnectionError, CloudAuthenticationError

logger = logging.getLogger("edge.sync")

# Global property for compatibility
def get_cloud_token():
    return cloud_client.token

async def fetch_token_loop():
    """
    Background loop that ensures the Cloud API token is pre-warmed and refreshed.
    If the cloud is down, logs and retries with backoff without crashing the edge service.
    """
    while True:
        if not cloud_client.token:
            try:
                await cloud_client.login_async(timeout=5.0)
                print("Successfully fetched Cloud API JWT token.", flush=True)
            except (CloudConnectionError, httpx.RequestError) as e:
                print(f"Token fetch: Cloud currently unreachable ({e}). Retrying in 5s...", flush=True)
            except CloudAuthenticationError as e:
                print(f"Token fetch: Authentication failed ({e}). Check API_EMAIL and API_PASSWORD.", flush=True)
            except Exception as e:
                print(f"Unexpected token fetch error: {e}. Retrying in 5s...", flush=True)
        await asyncio.sleep(5)


async def sync_worker():
    """
    Background worker that runs every 10 seconds to sync PENDING events
    from the local SQLite outbox to the Cloud API.
    """
    while True:
        try:
            await asyncio.to_thread(process_outbox)
        except Exception as e:
            print(f"Sync worker encountered an error: {e}", flush=True)

        await asyncio.sleep(10)


def process_outbox():
    """
    Reads PENDING events from SQLite outbox and attempts transmission to the Cloud API.
    Uses resilient CloudApiClient with Bearer token authentication and 401 retry.
    Falls back gracefully if the cloud is unreachable.
    """
    try:
        import main
        if getattr(main, "FAULT_STATE", {}).get("offline", False):
            print("Sync worker: Cloud simulated offline. Outbox sync paused.", flush=True)
            return
    except Exception:
        pass

    session = SessionLocal()
    try:
        pending_events = session.query(OutboxEvent).filter(OutboxEvent.status == 'PENDING').all()
        if not pending_events:
            return

        print(f"Sync worker found {len(pending_events)} pending events. Attempting to sync...", flush=True)

        for event in pending_events:
            try:
                payload = json.loads(event.payload)

                # Ensure eventId is present in payload for Cloud API idempotency
                if "eventId" not in payload:
                    payload["eventId"] = event.event_id

                response = cloud_client.post_telemetry_sync(payload, timeout=5.0)

                if response.status_code in (200, 201):
                    event.status = 'SYNCED'
                    session.commit()
                    print(f"Successfully synced event {event.event_id}", flush=True)
                else:
                    print(f"Failed to sync event {event.event_id}: HTTP {response.status_code} - {response.text}", flush=True)
            except (CloudConnectionError, httpx.RequestError) as e:
                print(f"Sync worker: Cloud unreachable ({e}). Events remain in outbox. Retrying next cycle.", flush=True)
                break  # Cloud is down, stop processing this batch
            except CloudAuthenticationError as e:
                print(f"Sync worker: Authentication failed ({e}). Retrying next cycle.", flush=True)
                break
            except Exception as e:
                print(f"Error processing outbox event {event.event_id}: {e}", flush=True)
    except Exception as e:
        print(f"Database error in sync worker: {e}", flush=True)
    finally:
        session.close()
