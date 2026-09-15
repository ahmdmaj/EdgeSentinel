# EdgeSentinel

EdgeSentinel is a resilient, edge-to-cloud anomaly detection platform designed for industrial IoT environments. It provides real-time sensor monitoring, machine learning inference at the edge, and robust cloud persistence to ensure continuous operational visibility even during intermittent network connectivity.

## System Architecture & Data Flow

The platform is designed around a distributed architecture that separates local edge ingestion and inference from centralized cloud aggregation.

1. **IoT Simulator (Sensors)**: Generates synthetic telemetry data (temperature, humidity, vibration, pressure).
2. **MQTT Broker (Eclipse Mosquitto)**: Acts as the local ingestion layer, accepting high-throughput telemetry streams from the edge sensors.
3. **Python Edge Node**: Subscribes to the MQTT broker, computes local Machine Learning anomaly scores using `scikit-learn`, and buffers the enriched telemetry locally using a SQLite outbox for offline-first resilience.
4. **Cloud API (Fastify / Node.js)**: A high-performance HTTP service that securely ingests batched telemetry from edge nodes and broadcasts real-time data via Server-Sent Events (SSE).
5. **Cloud Database (MySQL 8.0)**: Provides durable, relational persistence for the aggregated telemetry, devices, and anomaly events.

## Local Setup & Deployment

EdgeSentinel utilizes Docker Compose to guarantee deterministic and reproducible local environments. 

### Prerequisites
- Docker & Docker Compose
- Node.js (v22+)
- Python (3.11+)

### Initialization

Because the MySQL database volume is completely empty on its first boot, the Cloud API requires the database schema to be initialized before it can safely start up and seed default data. 

To prevent the API from crashing on its initial boot, you **must** sync the Prisma schema to the database first:

```bash
# 1. Ensure any old containers and volumes are cleared
docker compose down -v

# 2. Push the Prisma schema to the MySQL database
docker compose run --rm cloud-api npx prisma db push

# 3. Bring up the full orchestrated stack in the background
docker compose up -d --build
```

### Accessing the Services
- **Cloud API**: `http://localhost:3000`
- **Edge Node Health**: `http://localhost:8000`
- **Grafana Dashboards**: `http://localhost:3002`
- **Prometheus Metrics**: `http://localhost:9090`

## Documentation & Architecture Decision Records (ADRs)

Key engineering decisions and technical rationales are formally documented in the `docs/decisions/` directory:
- [ADR-001: Offline-First Edge Resiliency](docs/decisions/ADR-001-offline-first-edge.md)
- [ADR-002: Database Migration to MySQL](docs/decisions/ADR-002-database-migration-mysql.md)
- [ADR-003: Deterministic Docker Orchestration](docs/decisions/ADR-003-deterministic-docker-orchestration.md)
