import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import storage
from storage import Base, OutboxEvent, save_event_to_outbox

@pytest.fixture(autouse=True)
def setup_db():
    engine = create_engine("sqlite:///:memory:")
    storage.engine = engine
    storage.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_outbox_fifo_ordering():
    save_event_to_outbox("event-1", {"data": 1})
    save_event_to_outbox("event-2", {"data": 2})
    save_event_to_outbox("event-3", {"data": 3})
    
    session = storage.SessionLocal()
    pending_events = session.query(OutboxEvent).filter(OutboxEvent.status == 'PENDING').order_by(OutboxEvent.id).all()
    
    assert len(pending_events) == 3
    assert pending_events[0].event_id == "event-1"
    assert pending_events[1].event_id == "event-2"
    assert pending_events[2].event_id == "event-3"
    session.close()

@patch("sync.cloud_client.post_telemetry_sync")
def test_outbox_state_transitions(mock_post):
    import sync
    
    save_event_to_outbox("event-sync-1", {"data": 1})
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    sync.process_outbox()
    
    session = storage.SessionLocal()
    event = session.query(OutboxEvent).filter_by(event_id="event-sync-1").first()
    assert event.status == "SYNCED"
    session.close()

@patch("sync.cloud_client.post_telemetry_sync")
def test_outbox_exponential_backoff_simulated(mock_post):
    from app.sync.http_client import CloudConnectionError
    import sync
    
    save_event_to_outbox("event-sync-error", {"data": 2})
    
    mock_post.side_effect = CloudConnectionError("Unreachable")
    
    sync.process_outbox()
    
    session = storage.SessionLocal()
    event = session.query(OutboxEvent).filter_by(event_id="event-sync-error").first()
    assert event.status == "PENDING"
    session.close()
