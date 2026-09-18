import pytest
from inference import classify_severity
from decision_engine import evaluate_routing_policy
from app.storage.outbox import outbox_repo

def test_inference_severity_mapping():
    assert classify_severity(0.0) == "NORMAL"
    assert classify_severity(-0.08) == "NORMAL"
    assert classify_severity(-0.1) == "WARNING"
    assert classify_severity(-0.12) == "WARNING"
    assert classify_severity(-0.15) == "CRITICAL"
    assert classify_severity(-1.0) == "CRITICAL"

def test_decision_engine_routing():
    # If edge_cpu > 80, always CLOUD
    assert evaluate_routing_policy("CRITICAL", 100, 85.0) == "CLOUD"
    assert evaluate_routing_policy("NORMAL", 100, 85.0) == "CLOUD"
    
    # If CPU <= 80, and CRITICAL -> EDGE
    assert evaluate_routing_policy("CRITICAL", 100, 70.0) == "EDGE"
    
    # If CPU <= 80, and network latency > 200 -> EDGE
    assert evaluate_routing_policy("NORMAL", 250, 70.0) == "EDGE"
    
    # Otherwise HYBRID
    assert evaluate_routing_policy("NORMAL", 100, 70.0) == "HYBRID"
    assert evaluate_routing_policy("WARNING", 150, 50.0) == "HYBRID"

def test_outbox_fifo_ordering():
    # Clear outbox repo for the test
    outbox_repo._conn.execute("DELETE FROM outbox_events")
    outbox_repo._conn.commit()

    outbox_repo.insert_event("event-1", {"data": 1})
    outbox_repo.insert_event("event-2", {"data": 2})
    outbox_repo.insert_event("event-3", {"data": 3})

    batch = outbox_repo.get_pending_batch(10)
    assert len(batch) == 3
    assert batch[0]["event_id"] == "event-1"
    assert batch[1]["event_id"] == "event-2"
    assert batch[2]["event_id"] == "event-3"
