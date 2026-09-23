# Edge Fleet — Adaptive Routing & Device Isolation

This document describes how the EdgeSentinel fleet of simulated IoT devices is structured, how device isolation is enforced at the MQTT layer, and how the Edge Node's decision engine dynamically adapts its routing strategy based on real host metrics and network conditions.

---

## 1. Fleet Topology

The simulator (`services/simulator/main.py`) spawns **5 concurrent threads**, each representing a distinct device identity:

| Device ID | MQTT Topic | Thread |
| :--- | :--- | :--- |
| DEVICE-001 | `edgesentinel/devices/DEVICE-001/telemetry` | Thread-1 |
| DEVICE-002 | `edgesentinel/devices/DEVICE-002/telemetry` | Thread-2 |
| DEVICE-003 | `edgesentinel/devices/DEVICE-003/telemetry` | Thread-3 |
| DEVICE-004 | `edgesentinel/devices/DEVICE-004/telemetry` | Thread-4 |
| DEVICE-005 | `edgesentinel/devices/DEVICE-005/telemetry` | Thread-5 |

Each device publishes telemetry every **5 seconds** with a randomised startup jitter (0–3s) to prevent thundering herd on the broker.

---

## 2. Device Isolation via MQTT ACLs

Device cross-communication is prevented at the broker level. The Mosquitto ACL file (`infrastructure/mosquitto/config/mosquitto.acl`) enforces:

```
# Simulator user: write-only to its own telemetry subtopic
user device_client
topic write edgesentinel/devices/+/telemetry

# Edge service user: full read/write for its subscriber and control channels
user edge_client
topic readwrite edgesentinel/#
```

**What this prevents:**
- A `device_client` cannot **subscribe** to any topic (read-only devices are effectively blind to the rest of the fleet).
- A `device_client` publishing to `edgesentinel/devices/DEVICE-001/telemetry` cannot access `edgesentinel/devices/DEVICE-002/telemetry` or any other device's topic, because the `+` wildcard ACL restricts writes to the single-level wildcard pattern, which Mosquitto matches per-connection username.

---

## 3. Real System Metrics Collection

The Edge Node uses `psutil` and a raw TCP socket probe to gather actual system state before making routing decisions. This replaces the previous `random()` mocks.

**Source: `services/edge/app/metrics_collector.py`**

| Metric | Source | Description |
| :--- | :--- | :--- |
| `cpu_percent` | `psutil.cpu_percent(interval=0.1)` | Host CPU utilization (0–100%) |
| `memory_percent` | `psutil.virtual_memory().percent` | Host RAM utilization (0–100%) |
| `api_latency_ms` | `socket.create_connection()` timer | TCP round-trip time to Cloud API in ms. Returns 9999ms if unreachable. |

---

## 4. Adaptive Routing Rules

**Source: `services/edge/decision_engine.py`**

Routing decisions are evaluated in strict priority order for every incoming telemetry event:

| Priority | Condition | Decision | Rationale |
| :---: | :--- | :--- | :--- |
| 1 | `api_latency_ms ≥ 1000` | **`EDGE_ONLY`** | Cloud is unreachable. Buffer all events locally in the SQLite outbox until recovery. |
| 2 | `severity == CRITICAL` AND `latency < 300ms` | **`CLOUD_ONLY`** | Critical anomaly on a healthy link. Rush to cloud immediately. |
| 3 | `cpu_percent > 90%` AND `severity == NORMAL` | **`DEFER`** | System is overwhelmed. Drop low-priority events to protect edge node stability. |
| 4 | `cpu_percent > 70%` AND `severity == WARNING` | **`EDGE_ONLY`** | High load. Buffer warnings locally, avoid adding cloud overhead until CPU recovers. |
| 5 | `severity == CRITICAL` AND `latency ≥ 300ms` | **`HYBRID`** | Degraded link but anomaly is critical. Keep local copy AND attempt cloud sync. |
| 6 | *(default)* | **`HYBRID`** | Healthy conditions. Write to outbox and sync to cloud. |

---

## 5. Testing Adaptive Routing

### Simulate Network Outage
Stop the Cloud API container to make latency spike to 9999ms (timeout):
```bash
docker compose stop cloud-api
```
Watch Edge Node logs: all new events should log `processingDecision: EDGE_ONLY`.

When you restart the API, the SyncWorker drains the backlog in FIFO order:
```bash
docker compose start cloud-api
```

### Simulate High Latency via Fault Injection
Use the Edge Node's control plane to inject a synthetic latency value (overrides the real TCP probe):
```bash
curl -X POST http://localhost:8000/faults \
  -H "X-Edge-Admin-Token: edge-admin-token-123456" \
  -H "Content-Type: application/json" \
  -d '{"latency_ms": 1500}'
```
All subsequent events will route `EDGE_ONLY` until you clear the fault:
```bash
curl -X POST http://localhost:8000/faults \
  -H "X-Edge-Admin-Token: edge-admin-token-123456" \
  -H "Content-Type: application/json" \
  -d '{"latency_ms": 0}'
```
