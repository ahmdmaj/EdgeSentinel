# EdgeSentinel

**Resilient, Offline-First, Adaptive Edge-Cloud Anomaly Detection Platform**

EdgeSentinel is a distributed edge-cloud monitoring and anomaly detection platform designed to demonstrate how modern software systems can continue operating reliably when cloud connectivity is unreliable. 

The platform simulates an industrial monitoring environment where virtual devices continuously generate sensor data. Instead of sending every sensor reading to the cloud for processing, EdgeSentinel introduces an intelligent edge layer that preprocesses data, performs local ML inference, and makes adaptive decisions about processing locations.

---

## 🌟 Key Features

*   **Adaptive Edge-Cloud Processing:** A decision engine determines whether to process data at the edge, in the cloud, or using a hybrid approach based on network availability, latency, event severity, and model confidence.
*   **Offline-First Architecture:** The edge node can continue to operate and store important events locally (via SQLite) during network failures, automatically synchronizing with the cloud when connectivity is restored.
*   **Distributed Anomaly Detection:** Local machine learning inference (Isolation Forest) at the edge for immediate detection of critical events, with centralized analytics in the cloud.
*   **Monorepo Architecture:** The entire system—cloud frontend/backend, edge services, simulator, and ML models—is managed within a single repository for streamlined development and deployment.

---

## 🏗️ Architecture & Technology Stack

The system is split into cloud and edge environments, communicating via MQTT and HTTP:

### Cloud Environment
*   **Web Dashboard (`apps/web`):** Next.js, React, TypeScript, Tailwind CSS
*   **Cloud API (`apps/api`):** Node.js, Fastify, TypeScript, Prisma ORM
*   **Database:** PostgreSQL (Neon)

### Edge Environment
*   **Edge Node (`services/edge`):** Python, FastAPI, scikit-learn, SQLite
*   **IoT Simulator (`services/simulator`):** Python (Generates telemetry like temperature, vibration, etc.)
*   **Messaging:** Eclipse Mosquitto (MQTT)

### DevOps & Infrastructure
*   **Containerization:** Docker & Docker Compose
*   **CI/CD:** GitHub Actions
*   **Observability:** Prometheus & Grafana

---

## 📂 Repository Structure

Because this system has many moving parts, we use a **Monorepo** structure. Here is a breakdown of the project directories:

### `apps/` (Cloud Hosted)
*   **`apps/api/` (Cloud API):** The central brain in the cloud. A Fastify server that receives aggregated data from edge nodes, stores it, and serves it to the frontend.
*   **`apps/web/` (Frontend Dashboard):** The user interface where administrators can monitor edge devices, view charts, and manage incidents.

### `services/` (Edge & Local)
*   **`services/edge/` (Edge Node):** The Python service deployed physically on-site. Listens to local machines, uses ML to detect anomalies immediately, and stores data locally if offline.
*   **`services/simulator/` (IoT Simulator):** A Python script that generates fake sensor data (temperature, vibration) to test the software.

### `infrastructure/` (Third-party Tools)
*   **`infrastructure/mosquitto/`:** Configuration for the Eclipse Mosquitto MQTT Broker, used for local messaging between the simulator and edge node.

### `packages/` (Shared Code)
*   **`packages/`:** Shared code, TypeScript types, or utility functions used across both `apps/web` and `apps/api`.

### `ml/` (Machine Learning)
*   **`ml/`:** Workspace for Data Scientists. Contains Jupyter Notebooks, training data, and experiments before ML models are exported to the edge node.

### `docs/` (Documentation)
*   **`docs/`:** Detailed project documentation, API specs, and architecture diagrams.

---

## 🚀 Getting Started

To spin up the entire system locally:

1.  Ensure you have Docker and Docker Compose installed.
2.  Clone the repository and set up the necessary environment variables (copy `.env.example` to `.env`).
3.  Run the orchestration command:
    ```bash
    docker compose up
    ```
    This will boot up the API, Edge Node, Simulator, Postgres database, and Mosquitto broker on a shared virtual network.
