import asyncio
import httpx
import json
from storage import SessionLocal, OutboxEvent

cloud_token = None

async def fetch_token_loop():
    global cloud_token
    while True:
        if not cloud_token:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post("http://cloud-api:3000/api/v1/auth/login", json={"username": "admin", "password": "password"})
                    if resp.status_code == 200:
                        cloud_token = resp.json().get("token")
                        print("Successfully fetched Cloud API JWT token.", flush=True)
                    else:
                        print(f"Failed to fetch token, status: {resp.status_code}", flush=True)
            except Exception as e:
                print(f"Token fetch error: {e}. Retrying in 5s...", flush=True)
        await asyncio.sleep(5)

async def sync_worker():
    """
    Background worker that runs every 10 seconds to sync PENDING events
    from the local SQLite outbox to the Cloud API.
    """
    while True:
        if cloud_token:
            try:
                await asyncio.to_thread(process_outbox)
            except Exception as e:
                print(f"Sync worker encountered an error: {e}")
        
        await asyncio.sleep(10)

def process_outbox():
    global cloud_token
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
        
        headers = {"Authorization": f"Bearer {cloud_token}"} if cloud_token else {}
        
        with httpx.Client(timeout=5.0, headers=headers) as client:
            for event in pending_events:
                try:
                    payload = json.loads(event.payload)
                    
                    # Ensure eventId is present in payload for Cloud API idempotency
                    if "eventId" not in payload:
                        payload["eventId"] = event.event_id

                    response = client.post("http://cloud-api:3000/api/v1/telemetry", json=payload)
                    
                    if response.status_code in (200, 201):
                        event.status = 'SYNCED'
                        session.commit()
                        print(f"Successfully synced event {event.event_id}", flush=True)
                    elif response.status_code == 401:
                        print("Unauthorized (401) during sync. JWT invalid. Clearing token.", flush=True)
                        cloud_token = None
                        break
                    else:
                        print(f"Failed to sync event {event.event_id}: HTTP {response.status_code}", flush=True)
                except httpx.RequestError as e:
                    print(f"Sync worker: Cloud still unreachable. Will retry next cycle.", flush=True)
                    break # Cloud is down, stop processing this batch
                except Exception as e:
                    print(f"Error processing event {event.event_id}: {e}", flush=True)
    except Exception as e:
        print(f"Database error in sync worker: {e}", flush=True)
    finally:
        session.close()
