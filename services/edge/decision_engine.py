"""
decision_engine.py — Adaptive Routing Engine

Deterministic routing rules based on real host metrics and Cloud API latency.
All thresholds are documented in docs/testing/edge-fleet.md.

Routing decisions:
  EDGE_ONLY  — store locally, do not attempt cloud sync
  CLOUD_ONLY — route directly to cloud (critical priority)
  HYBRID     — queue locally AND attempt cloud sync
  DEFER      — silently drop or delay low-priority events under resource pressure
"""
from __future__ import annotations


# ── Threshold constants ─────────────────────────────────────────────────────
# Network
LATENCY_OFFLINE_MS    = 1000.0   # > 1000ms → treat link as offline
LATENCY_DEGRADED_MS   = 300.0    # 300-1000ms → degraded mode

# CPU
CPU_OVERLOAD_PERCENT  = 90.0     # > 90% → drop NORMAL events
CPU_HIGH_PERCENT      = 70.0     # > 70% + WARNING → defer to edge only

# Severity labels (must match inference.py)
SEV_CRITICAL = "CRITICAL"
SEV_WARNING  = "WARNING"
SEV_NORMAL   = "NORMAL"

# Decision labels (consumed by SyncWorker and Grafana dashboards)
DECISION_CLOUD_ONLY = "CLOUD_ONLY"
DECISION_EDGE_ONLY  = "EDGE_ONLY"
DECISION_HYBRID     = "HYBRID"
DECISION_DEFER      = "DEFER"


def evaluate_routing_policy(
    severity: str,
    network_latency_ms: float,
    edge_cpu_percent: float,
) -> str:
    """
    Determines how a telemetry payload should be routed based on real
    system conditions. Called from on_message() and ingest_telemetry_http()
    after ML inference assigns a severity.

    Priority order (highest to lowest):
      1. API unreachable → EDGE_ONLY for all severities
      2. CRITICAL severity → CLOUD_ONLY regardless of load
      3. CPU overloaded + NORMAL severity → DEFER (drop to protect system)
      4. High CPU + WARNING severity → EDGE_ONLY (buffer, retry later)
      5. Degraded network + CRITICAL → HYBRID (try cloud, keep local copy)
      6. Default → HYBRID
    """

    # Rule 1: API is unreachable — go offline, buffer locally
    if network_latency_ms >= LATENCY_OFFLINE_MS:
        return DECISION_EDGE_ONLY

    # Rule 2: CRITICAL anomaly on a healthy link — rush to cloud immediately
    if severity == SEV_CRITICAL and network_latency_ms < LATENCY_DEGRADED_MS:
        return DECISION_CLOUD_ONLY

    # Rule 3: CPU completely saturated — drop low-priority events to protect system
    if edge_cpu_percent > CPU_OVERLOAD_PERCENT and severity == SEV_NORMAL:
        return DECISION_DEFER

    # Rule 4: High CPU + WARNING — buffer locally to avoid adding cloud overhead
    if edge_cpu_percent > CPU_HIGH_PERCENT and severity == SEV_WARNING:
        return DECISION_EDGE_ONLY

    # Rule 5: CRITICAL on a degraded link — keep local copy AND attempt cloud
    if severity == SEV_CRITICAL and network_latency_ms >= LATENCY_DEGRADED_MS:
        return DECISION_HYBRID

    # Rule 6: Default — healthy link, queue locally and sync to cloud
    return DECISION_HYBRID
