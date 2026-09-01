import asyncio
import httpx
import json
from storage import SessionLocal, OutboxEvent

async def sync_worker():
    """
    Background worker that runs every 10 seconds to sync PENDING events
    from the local SQLite outbox to the Cloud API.
    """
    while True:
        try:
            await asyncio.to_thread(process_outbox)
        except Exception as e:
            print(f"Sync worker encountered an error: {e}")
        
        await asyncio.sleep(10)

def process_outbox():
    session = SessionLocal()
    try:
        pending_events = session.query(OutboxEvent).filter(OutboxEvent.status == 'PENDING').all()
        if not pending_events:
            return

        print(f"Sync worker found {len(pending_events)} pending events. Attempting to sync...", flush=True)
        
        with httpx.Client(timeout=5.0) as client:
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
