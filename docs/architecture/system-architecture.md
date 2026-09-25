# EdgeSentinel System Architecture

This document defines the final production architecture for the EdgeSentinel platform, detailing the flow of data, component responsibilities, and security boundaries.

## 1. High-Level Architecture Diagram

```mermaid
flowchart TD
    %% Define styles
    classDef edge fill:#f9f0ff,stroke:#d0bdf4,stroke-width:2px;
    classDef cloud fill:#e6f3ff,stroke:#90c2f9,stroke-width:2px;
    classDef external fill:#f5f5f5,stroke:#cccccc,stroke-width:2px;
    
    %% Devices
    subgraph Fleet ["Edge Device Fleet (Simulated)"]
        D1[Device 001]
        D2[Device 002]
        Dn[Device 005]
    end

    %% Edge Node Layer
    subgraph EdgeLayer ["Edge Node (Local Network)"]
        MQTT[Mosquitto Broker\nMQTT / port 1883]
        EdgeService[Edge Service\nPython / FastAPI]
        LocalDB[(SQLite\nOutbox Queue)]
        ML[ML Artifact\nIsolationForest]
    end

    %% Cloud Layer
    subgraph CloudLayer ["Cloud Environment (Docker Compose)"]
        Proxy[Nginx Reverse Proxy\nPorts 80/443]
        API[Cloud API\nNode.js / Fastify]
        Web[Web Dashboard\nNext.js]
        MySQL[(MySQL 8\nTelemetry Data)]
        
        %% Observability
        Prometheus[Prometheus\nMetrics Scraper]
        Grafana[Grafana\nDashboards]
        Alertmanager[Alertmanager\nRouting]
    end
    
    User((Operator))

    %% Data Flow
    D1 & D2 & Dn -- "MQTT (Restricted ACL)" --> MQTT
    MQTT -- "Subscribe" --> EdgeService
    ML -. "Loads via Volume" .-> EdgeService
    
    EdgeService -- "Buffer (Offline)" --> LocalDB
    LocalDB -. "SyncWorker (FIFO)" .-> EdgeService
    
    EdgeService -- "POST /telemetry\n(HTTP)" --> Proxy
    Proxy -- "Routes to API" --> API
    API -- "Prisma ORM" --> MySQL
    
    User -- "HTTPS / JWT" --> Proxy
    Proxy -- "Routes to Web" --> Web
    Web -- "SSR / Client Fetch" --> API
    
    Prometheus -. "Scrape /metrics" .-> API & EdgeService
    Prometheus -- "Trigger Rules" --> Alertmanager
    Grafana -. "Query Data" .-> Prometheus

    %% Apply Classes
    class Fleet external
    class EdgeLayer edge
    class CloudLayer cloud
```

## 2. Component Responsibilities & Security Boundaries

### 2.1 The Edge Layer
* **IoT Fleet (Simulator):** Generates noisy baseline telemetry mimicking industrial sensors. **Security:** Completely isolated. Clients can only write to their own specific MQTT topic (e.g., `edgesentinel/devices/DEVICE-001/telemetry`) and cannot subscribe to others.
* **Mosquitto MQTT Broker:** Serves as the ingestion gateway on the edge network. Enforces the strict ACLs.
* **Edge Service (Python):** The brain of the local node. It subscribes to the broker, runs real-time ML inference (loading versioned `.joblib` models from disk), and dynamically routes data based on actual host CPU and API network latency.
* **SQLite Outbox:** Provides offline-first resilience. If the cloud is unreachable, the Edge Service buffers telemetry here and replays it in FIFO order once connectivity is restored.

### 2.2 The Cloud Layer
* **Nginx Reverse Proxy:** The single entry point to the cloud environment. Handles SSL termination and routes external traffic to the Web Dashboard or Cloud API, completely hiding internal service ports.
* **Cloud API (Node.js/Fastify):** The central data ingest and control plane. **Security:** Hardened with Helmet, CORS restrictions, global rate-limiting, and JWT-based Role-Based Access Control (RBAC). 
* **MySQL 8:** The primary persistent store. Optimized with composite descending indexes on the `telemetry` table to handle high-throughput time-series pagination queries.
* **Web Dashboard (Next.js):** Provides operators with a responsive, server-side rendered interface to visualize anomalies and manage edge devices in real-time.

### 2.3 The Observability Stack
* **Prometheus:** Scrapes `/metrics` endpoints from both the Edge Service and Cloud API every 15 seconds.
* **Grafana:** Visualizes metrics via pre-provisioned dashboards (e.g., "Edge Reliability Dashboard").
* **Alertmanager:** Evaluates rules (like `ApiDown` or `HighErrorRate`) and routes alerts to external channels (e.g., Slack or Email) when system objectives are breached.

## 3. Network Architecture
All cloud components run within an isolated Docker bridge network (`edgesentinel-network`). Services resolve each other by container name (e.g., `http://cloud-api:3000`). Only Nginx (`:80`, `:443`) and Grafana (`:3002` for internal monitoring) are bound to the host network interface. MySQL is heavily protected and never exposed to the public internet.
