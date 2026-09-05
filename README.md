# EdgeSentinel

[![CI Pipeline](https://github.com/your-org/EdgeSentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/EdgeSentinel/actions/workflows/ci.yml)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3.8-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Node.js](https://img.shields.io/badge/Node.js-v20-339933.svg?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Prometheus](https://img.shields.io/badge/Metrics-Prometheus-E6522C.svg?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Dashboards-Grafana-F46800.svg?logo=grafana&logoColor=white)](https://grafana.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Resilient, Offline-First, Adaptive Edge-Cloud Anomaly Detection Platform**

---

## 🎯 Project Vision

Mission-critical industrial IoT infrastructures (e.g., smart manufacturing plants, remote energy grids, predictive asset monitoring) cannot afford downtime or catastrophic blind spots caused by intermittent or severed cloud connectivity. Traditional architectures rely on naive cloud forwarding: when wide-area network (WAN) links degrade, sensor readings are lost, anomaly notifications are delayed, and physical hardware is left unprotected.

**EdgeSentinel** is an enterprise-grade, distributed edge-cloud platform built to guarantee zero-data-loss telemetry processing in hostile, bandwidth-constrained network topologies. By combining on-device Machine Learning inference, an adaptive routing decision engine, a transactional SQLite transactional outbox, and self-healing JWT security, EdgeSentinel enables edge environments to operate autonomously during severe cloud outages while maintaining full synchronization and observability when connectivity recovers.

---

## 🏗️ Architecture Overview

EdgeSentinel partitions workloads across edge nodes and centralized cloud clusters, leveraging asynchronous messaging and transactional outbox patterns.

```
+-----------------------------------------------------------------------------------------------+
|                                  PHYSICAL / SIMULATED ASSETS                                  |
|                                                                                               |
|                       +-----------------------------------------------+                       |
|                       |            Virtual Device Simulator           |                       |
|                       |   [Temperature, Vibration, Humidity, Pressure]|                       |
|                       +-----------------------+-----------------------+                       |
+-----------------------------------------------|-----------------------------------------------+
                                                | MQTT Pub (`edgesentinel/devices/+/telemetry`)
                                                v
+-----------------------------------------------------------------------------------------------+
| EDGE ENVIRONMENT                                                                              |
|                                                                                               |
|  +-----------------------------+                                                              |
|  | Mosquitto MQTT Broker:1883  |                                                              |
|  +--------------+--------------+                                                              |
|                 | MQTT Sub                                                                    |
|                 v                                                                             |
|  +-----------------------------------------------------------------------------------------+  |
|  | Edge Service (Python 3.11, FastAPI, paho-mqtt v2)                                       |  |
|  |                                                                                         |  |
|  |  [Telemetry Ingest] -> [Isolation Forest ML] -> [Adaptive Decision Engine]              |  |
|  |                              (Score & Classify)      (Local vs Cloud vs Hybrid)         |  |
|  |                                                                  |                      |  |
|  |                 +------------------------------------------------+                      |  |
|  |                 |                                                                       |  |
|  |        [Cloud Reachable?]                                                               |  |
|  |             /        \                                                                  |  |
|  |       YES  /          \  NO (Simulated Fault / Network Drop)                            |  |
|  |           v            v                                                                |  |
|  |     +-----------+  +-------------------------------+                                    |  |
|  |     | HTTP Live |  | SQLite Outbox Table (OutboxDB)|                                    |  |
|  |     | Forwarder |  | (Transactional Buffer Store)  |                                    |  |
|  |     +-----+-----+  +---------------+---------------+                                    |  |
|  |           |                        |                                                    |  |
|  |           |                        v                                                    |  |
|  |           |        +-------------------------------+                                    |  |
|  |           |        | Background Replay Sync Worker |                                    |  |
|  |           |        +---------------+---------------+                                    |  |
|  |           +------------------------+                                                    |  |
|  |                                    |                                                    |  |
|  |  Self-Healing Token Loop           | HTTP POST /api/v1/telemetry                        |  |
|  |  (Background JWT Authenticator)    | (Bearer Token + Idempotency ID)                    |  |
|  +------------------------------------|----------------------------------------------------+  |
+---------------------------------------|-------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------------------+
| CLOUD ENVIRONMENT                                                                             |
|                                                                                               |
|  +-----------------------------------------------------------------------------------------+  |
|  | Cloud API (Node.js 20, Fastify, TypeScript)                                             |  |
|  | - Token Authority: `/api/v1/auth/login` (Signed HS256 JWT)                              |  |
|  | - Telemetry Ingestion: Deduplication cache (`eventId` idempotency window)               |  |
|  | - Real-Time Broadcast: Server-Sent Events (SSE) stream hub                              |  |
|  | - System Health & Instrumentation: `/health` & `/metrics`                               |  |
|  +-------------------+-----------------------------------------+---------------------------+  |
|                      |                                         |                              |
|                      | SSE (`/api/v1/telemetry/stream`)        | SQL Connection Pool          |
|                      v                                         v                              |
|  +---------------------------------------+  +----------------------------------------------+  |
|  | Operator Dashboard (Next.js 15, React)|  | PostgreSQL Database (postgres:15-alpine)     |  |
|  | - Live streaming telemetry feed       |  | - Persistent Cloud Storage                   |  |
|  | - Dynamic fault injection controls    |  +----------------------------------------------+  |
|  +---------------------------------------+                                                    |
+-----------------------------------------------------------------------------------------------+
                                        |
                                        v Scraped every 15s
+-----------------------------------------------------------------------------------------------+
| OBSERVABILITY STACK                                                                           |
|                                                                                               |
|  +-----------------------------------------------------------------------------------------+  |
|  | Prometheus Server (prom/prometheus:9090)                                                |  |
|  | - Scrapes `edge-service:8000/metrics` (tracks `events_processed_total`)                    |  |
|  | - Scrapes `cloud-api:3000/metrics` (tracks `cloud_events_received_total`)                  |  |
|  +--------------------------------------------+--------------------------------------------+  |
|                                               |                                               |
|                                               v                                               |
|  +-----------------------------------------------------------------------------------------+  |
|  | Grafana (grafana/grafana:3002)                                                          |  |
|  | - End-to-end event throughput, ingestion latency, and edge-vs-cloud routing breakdown   |  |
|  +-----------------------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------------+
```

### Core Architecture Highlights

1. **Adaptive Edge-Cloud Routing**:
   The edge decision engine inspects every reading across three dimensions:
   - **Severity Level**: `NORMAL`, `WARNING`, or `CRITICAL` generated by the Isolation Forest model.
   - **Network Latency**: Moving average or injected network latency ($ms$).
   - **Local Resource Utilization**: Edge CPU load and memory constraints.
   Telemetry is classified into one of three execution paths:
   - `EDGE_ONLY`: High network latency or severe degradation; processing executed locally.
   - `CLOUD_ONLY`: Nominal network conditions with low-severity events.
   - `HYBRID`: Critical anomalies prioritized locally, with batch replication to the cloud for historical audit trails.

2. **Offline-First Resilience & Outbox Sync**:
   - If the cloud endpoint is unreachable or in a forced outage state, live HTTP dispatch safely aborts.
   - Events are atomically committed to a local SQLite persistent outbox table (`status = 'PENDING'`).
   - An asynchronous background worker continuously monitors network health and drains the queue in FIFO sequence once connectivity is re-established.
   - Replay bursts are bounded and idempotent, preventing message duplication or memory starvation.

3. **Robust Security & Lifecycle**:
   - Cloud API routes are secured behind signed HS256 JWT tokens.
   - Edge nodes execute an automated background token acquisition and refresh loop.
   - If token expiration or invalidation occurs (`401 Unauthorized`), the token is evicted, outgoing live events seamlessly divert to the outbox, and authentication renegotiation triggers automatically.

---

## 💻 Technology Stack

| Layer | Technologies | Key Libraries & Specifications |
|---|---|---|
| **Edge Compute** | Python 3.11, FastAPI, Uvicorn | `paho-mqtt` (v2 API), `scikit-learn` (Isolation Forest), `SQLAlchemy`, `httpx` |
| **Local Persistence** | SQLite 3 | Embedded transactional outbox storage |
| **Edge-Device Messaging** | Eclipse Mosquitto 2.0 | MQTT v3.1.1/v5 broker |
| **Cloud Backend** | Node.js 20, Fastify, TypeScript | `@fastify/jwt`, `@fastify/cors`, `zod` schema validation, `prom-client` |
| **Cloud Persistence** | PostgreSQL 15 | Relational data store |
| **Operator Frontend** | Next.js 15, React, TypeScript | Tailwind CSS, Server-Sent Events (SSE) streaming, Glassmorphism UI |
| **Observability** | Prometheus, Grafana | `prometheus-fastapi-instrumentator`, `prom-client`, PromQL |
| **Containerization** | Docker, Docker Compose | Multi-stage Docker builds, bridge networking |
| **Continuous Integration** | GitHub Actions | Automated multi-runtime validation & Docker container builds |

---

## 🚀 Getting Started

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose (v2.20+)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/EdgeSentinel.git
cd EdgeSentinel
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
*(Default environment values are pre-configured to work out of the box).*

### 3. Spin Up the Full Stack
Execute the following single command from the project root to build and start all containers in detached mode:

```bash
docker compose up -d --build
```

### 4. Verify Running Services

```bash
docker compose ps
```

| Service | Host URL | Port Mapping | Description |
|---|---|---|---|
| **Web Dashboard** | [http://localhost:3000](http://localhost:3000) | `3000:3000` | Real-time SSE operator dashboard & fault injection controls |
| **Cloud API** | [http://localhost:3000](http://localhost:3000) | `3000:3000` | REST API, SSE streaming endpoint, and JWT authentication |
| **Edge Service** | [http://localhost:8000](http://localhost:8000) | `8000:8000` | FastAPI edge engine, ML inference & fault control API |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | `9090:9090` | Time-series metrics engine & PromQL explorer |
| **Grafana** | [http://localhost:3002](http://localhost:3002) | `3002:3000` | Visual observability dashboards (`admin` / `admin`) |
| **Mosquitto** | `localhost:1883` | `1883:1883` | Local device MQTT broker |

---

## 🧪 Interactive Resilience & Fault Testing

EdgeSentinel includes an on-demand fault injection engine to evaluate system behavior under real-world network failure scenarios:

### Scenario A: Simulate Cloud Outage (Offline-First Outbox Test)
```bash
# 1. Force the edge node into offline mode
curl -X POST http://localhost:8000/faults \
  -H "Content-Type: application/json" \
  -d '{"offline": true}'

# 2. Inspect the outbox buffering
# Notice that MQTT messages continue processing, ML inference runs uninterrupted,
# and events are saved safely to the SQLite outbox without dropping data.

# 3. Restore cloud connectivity
curl -X POST http://localhost:8000/faults \
  -H "Content-Type: application/json" \
  -d '{"offline": false}'

# 4. Observe the background worker automatically flush all buffered events upstream.
```

### Scenario B: Inject Network Latency (Adaptive Decision Routing Test)
```bash
# Inject 350ms of network latency
curl -X POST http://localhost:8000/faults \
  -H "Content-Type: application/json" \
  -d '{"latency_ms": 350}'

# Inspect the edge logs: the decision engine will automatically reroute processing
# decisions from CLOUD_ONLY to EDGE_ONLY or HYBRID.
```

---

## 📊 Observability & Metrics

Prometheus automatically scrapes both edge and cloud services across the internal Docker network (`edgesentinel-network`):

- **Edge Metrics**: `http://edge-service:8000/metrics`
  - `events_processed_total`: Cumulative counter incremented per MQTT telemetry message processed.
  - HTTP request latencies and system process metrics via `prometheus-fastapi-instrumentator`.
- **Cloud Metrics**: `http://cloud-api:3000/metrics`
  - `cloud_events_received_total`: Cumulative counter incremented on every telemetry ingestion POST.
  - Node.js event loop lag, memory RSS, and V8 heap statistics via `prom-client`.

### Key PromQL Expressions
```promql
# Rate of telemetry events processed on the edge
rate(events_processed_total[1m])

# Rate of telemetry ingestion on the cloud
rate(cloud_events_received_total[1m])

# System End-to-End Success Ratio
rate(cloud_events_received_total[1m]) / rate(events_processed_total[1m])
```

---

## ⚙️ Continuous Integration (CI/CD)

Automated testing and build verification are managed via GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)):
- **Multi-Runtime Environment Verification**: Validates Node.js 20 and Python 3.11 dependency trees.
- **Docker Container Build Tests**: Compiles `edge-service`, `cloud-api`, and `simulator` multi-stage containers to ensure integration sanity before code merges into `main`.
- **Compose Linting**: Runs `docker compose config` against production manifests to validate port and volume specifications.

---

## 📁 Repository Structure

```
EdgeSentinel/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI pipeline
├── apps/
│   ├── api/                     # Cloud REST API & SSE Hub (Fastify, TypeScript, prom-client)
│   └── web/                     # Operator Dashboard (Next.js 15, Tailwind CSS, SSE client)
├── services/
│   ├── edge/                    # Resilient Edge Node (FastAPI, scikit-learn, SQLite outbox)
│   └── simulator/               # IoT Industrial Device Simulator (MQTT publisher)
├── infrastructure/
│   ├── mosquitto/               # Mosquitto broker configuration
│   └── prometheus/              # Prometheus scrapers (edge-service & cloud-api)
├── packages/                    # Shared TypeScript interfaces & types
├── ml/                          # Isolation Forest training pipelines & models
├── docs/                        # Architecture decisions & technical specifications
└── docker-compose.yml           # Unified orchestration manifest
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
