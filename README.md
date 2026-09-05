# EdgeSentinel

[![CI Pipeline](https://github.com/your-org/EdgeSentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/EdgeSentinel/actions/workflows/ci.yml)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3.8-blue.svg)](https://www.docker.com/)
[![Node.js](https://img.shields.io/badge/Node.js-v20-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-yellow.svg)](https://www.python.org/)
[![Observability](https://img.shields.io/badge/Metrics-Prometheus%20%26%20Grafana-orange.svg)](https://prometheus.io/)

> **Resilient, Offline-First, Adaptive Edge-Cloud Anomaly Detection Platform**

EdgeSentinel is a distributed industrial monitoring and edge-cloud anomaly detection platform engineered to demonstrate high-availability, fault-tolerant operations in hostile network environments where cloud connectivity is intermittent or degraded.

The platform simulates an industrial IoT deployment where physical telemetry streams into an intelligent local edge node. Rather than naive blind forwarding to the cloud, EdgeSentinel performs on-site ML anomaly scoring, executes dynamic edge vs. cloud routing policies, buffers unacknowledged transactions locally during network outages, and automatically resumes bidirectional synchronization when cloud connectivity recovers.

---

## 🏛️ System Architecture

```
                                  +-----------------------------+
                                  |    Virtual IoT Simulator    |
                                  | (Temp, Vib, Humidity, Press)|
                                  +--------------+--------------+
                                                 | MQTT (Port 1883)
                                                 v
                                  +-----------------------------+
                                  |   Mosquitto MQTT Broker     |
                                  +--------------+--------------+
                                                 |
                                                 v
+-----------------------------------------------------------------------------------------------+
| EDGE ENVIRONMENT (services/edge)                                                              |
|                                                                                               |
|  +-----------------------+     +-----------------------+     +-----------------------------+  |
|  |   MQTT Ingestion      | --> |  ML Anomaly Detector  | --> |     Decision Engine         |  |
|  |   (paho-mqtt v2)      |     |  (Isolation Forest)   |     | (Severity, Latency, CPU)    |  |
|  +-----------------------+     +-----------------------+     +--------------+--------------+  |
|                                                                             |                 |
|                                          +----------------------------------+                 |
|                                          |                                                    |
|                                [Cloud Connected?]                                             |
|                                       /      \                                                |
|                                 YES  /        \  NO / Outage                                  |
|                                     v          v                                              |
|                         +---------------+  +--------------------------+                       |
|                         | Live HTTP Post|  |  SQLite Outbox Storage   |                       |
|                         | (JWT Bearer)  |  |  (Persistent Local Queue)|                       |
|                         +---------------+  +------------+-------------+                       |
|                                 |                       |                                     |
|                                 |                       v                                     |
|                                 |          +--------------------------+                       |
|                                 |          | Background Sync Worker   |                       |
|                                 |          | (Automatic Retry & Sync) |                       |
|                                 |          +------------+-------------+                       |
|                                 +-----------------------+                                     |
+---------------------------------------------|-------------------------------------------------+
                                              | HTTP POST /api/v1/telemetry (Bearer Token)
                                              v
+-----------------------------------------------------------------------------------------------+
| CLOUD ENVIRONMENT (apps/api & apps/web)                                                       |
|                                                                                               |
|  +-------------------------------------------------------------+                              |
|  | Fastify Cloud API (apps/api)                                |                              |
|  | - JWT Authentication & Session Token Issuer                 |                              |
|  | - Ingestion Deduplication (Idempotent by eventId)           |                              |
|  | - SSE Real-time Broadcast Hub                               |                              |
|  | - /health & /metrics Endpoints                              |                              |
|  +------------------------------+------------------------------+                              |
|                                 |                                                             |
|                 +---------------+---------------+                                             |
|                 | Server-Sent Events            | Internal Network                            |
|                 v                               v                                             |
|  +-----------------------------+  +-----------------------------+                             |
|  | Next.js Real-time Dashboard |  | PostgreSQL Database         |                             |
|  | (Live Telemetry & Controls) |  | (Persistent Cloud Store)    |                             |
|  +-----------------------------+  +-----------------------------+                             |
+-----------------------------------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------------------------------+
| OBSERVABILITY STACK (infrastructure/prometheus & Grafana)                                     |
|                                                                                               |
|  +-------------------------------------------------------------+                              |
|  | Prometheus (prom/prometheus:9090)                           |                              |
|  | - Scrapes edge-service:8000/metrics (events_processed_total)|                              |
|  | - Scrapes cloud-api:3000/metrics (cloud_events_received_total)|                            |
|  +------------------------------+------------------------------+                              |
|                                 |                                                             |
|                                 v                                                             |
|  +-------------------------------------------------------------+                              |
|  | Grafana (grafana/grafana:3002)                              |                              |
|  | - Visualizes end-to-end metrics, latency & error rates      |                              |
|  +-------------------------------------------------------------+                              |
+-----------------------------------------------------------------------------------------------+
```

---

## 🌟 Key Features

- **Offline-First Resilience**: An edge-native SQLite outbox buffers telemetry events whenever connectivity degrades or the cloud becomes unreachable. An asynchronous background sync worker systematically drains and replays stored events in FIFO order once connection is re-established.
- **Adaptive Edge Decision Engine**: Evaluates whether telemetry should be processed locally at the edge, forwarded to the cloud, or split into a hybrid pipeline based on model anomaly score, simulated network latency, and current CPU consumption.
- **On-Device ML Inference**: Embedded scikit-learn Isolation Forest algorithm computes real-time anomaly scores directly on the edge node without round-trip network delays.
- **Fault Injection Framework**: Integrated software controls allow dynamic simulation of cloud outages (`offline=true`) and artificial transmission latencies (`latency_ms`), proving resilience under active failure conditions.
- **Zero-Polling SSE Telemetry**: Real-time event streaming via Server-Sent Events (SSE) from Fastify to Next.js 15 frontend, maintaining sub-second updates without wasteful client polling.
- **Comprehensive Observability**: Prometheus automatically scrapes both `edge-service` and `cloud-api` endpoints on the internal Docker network. Grafana provides unified dashboards on port `3002`.
- **JWT Security & Token Lifecycle**: Secure end-to-end communication using HS256 JWT bearer tokens. Edge services authenticate automatically upon container boot and transparently handle token expiration and reconnection.
- **Automated CI/CD Pipeline**: GitHub Actions validates Node.js/Python dependencies and verifies container builds on every push and pull request.

---

## 📂 Repository Structure

```
EdgeSentinel/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI pipeline (build & environment tests)
├── apps/
│   ├── api/                     # Cloud REST API & SSE Hub (Fastify, TypeScript, prom-client)
│   └── web/                     # Operator Dashboard (Next.js 15, Tailwind CSS, SSE)
├── services/
│   ├── edge/                    # Resilient Edge Node (FastAPI, scikit-learn, SQLite outbox)
│   └── simulator/               # IoT Industrial Device Simulator (MQTT publisher)
├── infrastructure/
│   ├── mosquitto/               # Eclipse Mosquitto configuration
│   └── prometheus/              # Prometheus scrapers (edge-service & cloud-api)
├── packages/                    # Shared TypeScript contracts & models
├── ml/                          # Isolation Forest training notebooks & models
├── docs/                        # Architecture decisions & technical specifications
└── docker-compose.yml           # Unified orchestration for all 7 platform services
```

---

## 🚀 Quick Start (Docker Compose)

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose (v2.20+)
- Git

### 1. Clone & Configure
```bash
git clone https://github.com/your-org/EdgeSentinel.git
cd EdgeSentinel

# Environment configuration
cp .env.example .env   # (Defaults are pre-configured for local execution)
```

### 2. Launch the Entire Platform
```bash
docker compose up -d --build
```

### 3. Access Services

| Service | Address | Description |
|---|---|---|
| **Web Dashboard** | [http://localhost:3000](http://localhost:3000) (or web port) | Live telemetry & fault injection UI |
| **Cloud API** | [http://localhost:3000](http://localhost:3000) | Fastify REST API & SSE endpoint |
| **Edge Service** | [http://localhost:8000](http://localhost:8000) | FastAPI edge node & local fault control |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | Metric collection & PromQL console |
| **Grafana** | [http://localhost:3002](http://localhost:3002) | Visualization & dashboards (`admin:admin`) |
| **Mosquitto** | `localhost:1883` | Internal MQTT broker |

---

## 📊 Observability & Metrics

Prometheus monitors system health and scrapes custom business and operational metrics across the Docker network every 15 seconds:

### Scraped Endpoints
- `edge-service:8000/metrics`: Exposes FastAPI request durations, resource stats, and custom counter `events_processed_total`.
- `cloud-api:3000/metrics`: Exposes Node.js garbage collection, event loop lag, HTTP metrics, and custom counter `cloud_events_received_total`.

### Sample PromQL Queries
```promql
# Rate of telemetry events processed at the edge
rate(events_processed_total[1m])

# Rate of cloud telemetry ingestion
rate(cloud_events_received_total[1m])

# Edge vs Cloud delivery ratio
rate(cloud_events_received_total[1m]) / rate(events_processed_total[1m])
```

---

## 🧪 Fault Injection & Resilience Testing

Simulate network degradation or total cloud severance via the Edge Service HTTP API:

### 1. Force Offline Mode (Cloud Outage)
```bash
curl -X POST http://localhost:8000/faults \
  -H "Content-Type: application/json" \
  -d '{"offline": true}'
```
*Result*: Telemetry forwarding raises connection errors; events immediately divert to the SQLite outbox.

### 2. Restore Connectivity (Outbox Draining)
```bash
curl -X POST http://localhost:8000/faults \
  -H "Content-Type: application/json" \
  -d '{"offline": false}'
```
*Result*: Background worker detects connectivity, consumes all pending outbox records, and syncs them upstream.

### 3. Inject Simulated Network Latency
```bash
curl -X POST http://localhost:8000/faults \
  -H "Content-Type: application/json" \
  -d '{"latency_ms": 350}'
```
*Result*: Decision engine detects high latency and shifts processing priority to edge-only execution.

---

## 🔒 Security Model

- **Authentication**: `POST /api/v1/auth/login` issues signed JSON Web Tokens (HS256).
- **Bearer Protection**: All telemetry ingestion and inspection routes require `Authorization: Bearer <token>`.
- **Automatic Token Re-issuance**: The Edge Node automatically negotiates fresh tokens on cold starts or upon receiving `401 Unauthorized`.
- **Idempotent Ingestion**: Every event carries a UUID `eventId`. Duplicate deliveries during reconnection replays are acknowledged with HTTP 200 without creating redundant database entries.

---

## ⚙️ CI/CD Workflow

The repository includes a GitHub Actions continuous integration pipeline ([.github/workflows/ci.yml](.github/workflows/ci.yml)) configured to run on all pushes and pull requests targeting `main`:
1. **Environment Setup & Dependency Verification**:
   - Sets up Node.js 20 and runs clean installation of `apps/api` dependencies.
   - Sets up Python 3.11 and installs requirements for `services/edge` and `services/simulator`.
2. **Container Build Validation**:
   - Compiles and verifies Docker images for `edge-service`, `cloud-api`, and `simulator`.
   - Validates compose service manifests using `docker compose config`.

---

## 🗺️ Milestone Roadmap

| Milestone | Scope | Status |
|---|---|---|
| **1. Foundation** | Monorepo scaffold, Docker Compose orchestration, MQTT broker | ✅ Complete |
| **2. Edge Ingestion** | IoT Simulator + Edge Node MQTT subscriber pipeline | ✅ Complete |
| **3. Edge Intelligence** | Isolation Forest ML anomaly scoring + Adaptive Decision Engine | ✅ Complete |
| **4. Offline Resilience** | SQLite Outbox pattern + resilient background sync worker | ✅ Complete |
| **5. Cloud Visualization** | Next.js 15 operator dashboard + Server-Sent Events (SSE) | ✅ Complete |
| **6. Security Hardening** | JWT authentication, bearer authorization, edge auto-login | ✅ Complete |
| **7. Fault Injection** | Dynamic latency and outage injection APIs for testing | ✅ Complete |
| **8. Observability** | Prometheus metric scrapers + Grafana dashboards | ✅ Complete |
| **9. Polish & CI/CD** | GitHub Actions pipeline + portfolio-grade documentation | ✅ Complete |

---

## 📄 License
This project is licensed under the MIT License.
