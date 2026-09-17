import pytest
from decision_engine import evaluate_routing_policy

def test_routing_policy_cpu_overload():
    # High CPU should route to CLOUD regardless of severity or latency
    decision = evaluate_routing_policy("CRITICAL", 300, 85.0)
    assert decision == "CLOUD"

def test_routing_policy_critical_severity():
    decision = evaluate_routing_policy("CRITICAL", 50, 60.0)
    assert decision == "EDGE"

def test_routing_policy_high_latency():
    decision = evaluate_routing_policy("WARNING", 250, 60.0)
    assert decision == "EDGE"

def test_routing_policy_normal():
    decision = evaluate_routing_policy("NORMAL", 50, 60.0)
    assert decision == "HYBRID"
