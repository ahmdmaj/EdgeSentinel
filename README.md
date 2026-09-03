# EdgeSentinel

**Resilient, Offline-First, Adaptive Edge-Cloud Anomaly Detection Platform**

EdgeSentinel is a distributed edge-cloud monitoring and anomaly detection platform designed to demonstrate how modern software systems can continue operating reliably when cloud connectivity is unreliable.

The platform simulates an industrial monitoring environment where virtual devices continuously generate sensor data. Instead of sending every sensor reading to the cloud for processing, EdgeSentinel introduces an intelligent edge layer that preprocesses data, performs local ML inference, and makes adaptive decisions about processing location — all secured end-to-end with JWT authentication.

---

## 🌟 Key Features

*   **Adaptive Edge-Cloud Processing:** A decision engine determines whether to process data at the edge, in the cloud, or using a hybrid approach based on network availability, latency, event severity, and model confidence.
*   **Offline-First Architecture:** The edge node continues to operate and stores critical events locally (SQLite outbox) during network failures, automatically synchronizing with the cloud when connectivity is restored.
*   **Distributed Anomaly Detection:** Local ML inference (Isolation Forest) at the edge for immediate detection of critical events, with centralized analytics available via the Cloud API.
*   **Real-Time SSE Dashboard:** The web frontend connects to the Cloud API via Server-Sent Events (SSE) and streams live telemetry without polling.
*   **JWT Security & Access Control:** All Cloud API endpoints are protected with signed JWT Bearer tokens. Edge nodes authenticate on startup and automatically re-fetch tokens if they expire or the cloud was temporarily unreachable.
*   **Idempotent Event Ingestion:** Duplicate telemetry events from retried transmissions are safely deduplicated using event IDs.
*   **Monorepo Architecture:** The entire system — cloud frontend/backend, edge services, simulator, and ML models — is managed within a single repository for streamlined development and deployment.

---

## 🏗️ Architecture & Technology Stack

The system is split into cloud and edge environments, communicating via MQTT and HTTP:

### Cloud Environment
*   **Web Dashboard (`apps/web`):** Next.js, React, TypeScript, Tailwind CSS — real-time SSE-powered telemetry feed
*   **Cloud API (`apps/api`):** Node.js, Fastify, TypeScript — JWT-protected REST API with SSE streaming
*   **Authentication:** `@fastify/jwt` — HS256 signed tokens, configurable via `JWT_SECRET` env var

### Edge Environment
*   **Edge Node (`services/edge`):** Python, FastAPI, scikit-learn, SQLite — runs on-site, authenticates with the cloud on startup
*   **IoT Simulator (`services/simulator`):** Python — generates realistic telemetry (temperature, vibration, humidity, pressure)
*   **Messaging:** Eclipse Mosquitto (MQTT broker for local device communication)

### DevOps & Infrastructure
*   **Containerization:** Docker & Docker Compose
*   **CI/CD:** GitHub Actions
*   **Observability:** Prometheus & Grafana

---

## 📂 Repository Structure

```
EdgeSentinel/
├── apps/
│   ├── api/              # Cloud API (Fastify, JWT, SSE)
│   └── web/              # Frontend Dashboard (Next.js, SSE client)
├── services/
│   ├── edge/             # Edge Node (FastAPI, ML inference, SQLite outbox, JWT auth)
│   └── simulator/        # IoT device simulator
├── infrastructure/
│   └── mosquitto/        # MQTT broker configuration
├── packages/             # Shared TypeScript types & utilities
├── ml/                   # ML training notebooks & model experiments
└── docs/                 # Architecture diagrams & API specs
```

---

## 🔐 Security Model (Milestone 6)

All protected Cloud API endpoints require a valid JWT Bearer token in the `Authorization` header.

### Obtaining a Token

```bash
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

**Response:**
```json
{ "token": "<signed-jwt>" }
```

### Using the Token

```bash
# Fetch recent telemetry events
curl http://localhost:3000/api/v1/telemetry \
  -H "Authorization: Bearer <token>"

# Post a new telemetry event
curl -X POST http://localhost:3000/api/v1/telemetry \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Connect to the SSE stream
curl http://localhost:3000/api/v1/telemetry/stream \
  -H "Authorization: Bearer <token>"
```

**Protected Endpoints:**

| Method | Path | Auth Required |
|--------|------|:---:|
| `POST` | `/api/v1/auth/login` | ❌ |
| `GET`  | `/health` | ❌ |
| `GET`  | `/api/v1/telemetry` | ✅ |
| `POST` | `/api/v1/telemetry` | ✅ |
| `GET`  | `/api/v1/telemetry/stream` | ✅ |

### Edge Node Auth Flow

1. On startup, the edge node fires a background `fetch_token_loop` task.
2. It POSTs to `/api/v1/auth/login` every 5 seconds until a token is retrieved.
3. If the cloud is down at startup, telemetry is cached in the SQLite outbox — no data is lost.
4. Once authenticated, every `httpx` request (live forwarding + background sync) carries `Authorization: Bearer <token>`.
5. A `401 Unauthorized` response automatically clears the local token and triggers a re-fetch.

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose installed
- (Optional) Node.js 20+ for local API development

### Running the Full Stack

```bash
# 1. Clone the repository
git clone https://github.com/your-org/EdgeSentinel.git
cd EdgeSentinel

# 2. Copy environment variables
cp .env.example .env
# Edit .env to set JWT_SECRET (optional — defaults to "supersecret")

# 3. Boot the entire stack
docker compose up
```

This will start:
- **Cloud API** on `http://localhost:3000`
- **Web Dashboard** on `http://localhost:3001`
- **Edge Node** on `http://localhost:8000`
- **Mosquitto MQTT Broker** on `localhost:1883`
- **IoT Simulator** (publishes MQTT messages continuously)

### Running the Cloud API Locally (Dev Mode)

```bash
cd apps/api
npm install
npm run dev
```

---

## 📡 API Reference

### `GET /health`
Returns server health status. No authentication required.

### `POST /api/v1/auth/login`
Authenticates a user and returns a signed JWT.

**Body:** `{ "username": "admin", "password": "password" }`  
**Returns:** `{ "token": "<jwt>" }`

### `POST /api/v1/telemetry` 🔒
Ingest a telemetry event from an edge node. Validates schema via Zod, deduplicates by `eventId`, and broadcasts to all active SSE clients.

### `GET /api/v1/telemetry` 🔒
Returns the 50 most recent telemetry events as JSON.

### `GET /api/v1/telemetry/stream` 🔒
Opens a persistent Server-Sent Events (SSE) connection. Streams new telemetry events in real time as they arrive.

---

## 🗺️ Milestone Roadmap

| Milestone | Description | Status |
|-----------|-------------|--------|
| 1 | Monorepo scaffold, Docker Compose, MQTT broker | ✅ Complete |
| 2 | IoT Simulator + Edge Node MQTT pipeline | ✅ Complete |
| 3 | ML anomaly detection (Isolation Forest) + Decision Engine | ✅ Complete |
| 4 | Offline-first SQLite outbox + background sync worker | ✅ Complete |
| 5 | Real-time SSE dashboard (Cloud API + Next.js frontend) | ✅ Complete |
| 6 | JWT Authentication & API protection | 🔄 In Progress |
| 7 | Role-based access control (RBAC) | 🔜 Planned |
| 8 | Observability (Prometheus metrics + Grafana dashboards) | 🔜 Planned |

