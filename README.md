# EdgeSentinel 🛡️

[![CI Pipeline](https://github.com/ahmdmaj/EdgeSentinel/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/ahmdmaj/EdgeSentinel/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**EdgeSentinel is an engineered, offline-first edge-cloud anomaly detection platform.**

Built to demonstrate production-grade architectural patterns, EdgeSentinel simulates an industrial IoT fleet that feeds sensor telemetry through a highly resilient edge node up to a secure cloud dashboard. It goes beyond the "happy path" by natively handling catastrophic network failures, dynamic resource constraints, and automated CI/CD lifecycles.

## 🚀 Key Engineering Features

* **Offline-First Edge Resilience:** When the cloud API goes down, the Edge Node seamlessly buffers telemetry in a local SQLite Write-Ahead Log (WAL), replaying events in strict FIFO order upon recovery—guaranteeing zero data loss.
* **Adaptive Edge Routing:** A deterministic decision engine routes traffic based on *real* host CPU metrics (via `psutil`) and actual TCP socket latency to the cloud, dropping or deferring low-priority events during system duress.
* **ML Artifact Versioning:** Machine Learning isn't an afterthought. The `IsolationForest` anomaly detector is trained, serialized (`.joblib`), and loaded dynamically from disk via environment variables, allowing instant rollback of inference models without recompiling containers.
* **Automated CI/CD & Security:** GitHub Actions automatically tests, lint-checks, and scans for secrets (Gitleaks) on every commit. Pushing to `main` triggers Trivy vulnerability scans and publishes immutable container images to the GitHub Container Registry (GHCR).
* **Production Observability:** The entire stack is heavily instrumented. Prometheus scrapes custom business metrics, Grafana visualizes the fleet, and Alertmanager routes critical alerts (e.g., `ApiDown`, `EdgeOutboxStalled`) when SLAs are breached.

---

## 🏗️ System Architecture

EdgeSentinel separates concerns across three strict boundaries: the isolated IoT fleet, the local Edge Node, and the Cloud Environment. 

*See the complete [System Architecture Diagram & Component Breakdown](docs/architecture/system-architecture.md).*

---

## ⚡ Quick Start (Local Evaluation)

You can boot the entire production-like cluster locally on your machine using Docker Compose.

**1. Clone the repository:**
```bash
git clone https://github.com/ahmdmaj/EdgeSentinel.git
cd EdgeSentinel
```

**2. Configure the environment:**
```bash
# Generate the base environment file
cp .env.example .env
```

**3. Boot the stack:**
```bash
# This builds and starts the MQTT broker, MySQL, Fastify API, Python Edge Node, Next.js Web Dashboard, and the Observability Stack.
docker compose up --build -d
```

**4. Explore the system:**
- **Web Dashboard:** `http://localhost:3001` (Login with `admin@edgesentinel.local` / `S3cur3P@ssw0rd!`)
- **Grafana Metrics:** `http://localhost:3002` (Login with `admin` / `admin`)
- **API Health:** `http://localhost:3000/health`

---

## 📚 Portfolio Documentation & Evidence

This repository is built to be evaluated. Please review the following technical documents that prove the platform's reliability, security, and production readiness:

* 🏗️ **[System Architecture](docs/architecture/system-architecture.md)** — Data flow diagrams and security boundaries.
* ✅ **[Final Validation Report](docs/testing/final-validation-report.md)** — Master checklist and chaos testing results.
* 📈 **[Capacity & Load Test Report](docs/performance/capacity-report.md)** — k6 throughput metrics and resource utilization ceilings.
* 🚨 **[Disaster Recovery Runbook](docs/runbooks/disaster-recovery.md)** — RPO/RTO definitions and explicit database backup/restore procedures.
* 🚢 **[Release & Rollback SOP](docs/runbooks/release-and-rollback.md)** — Deployment procedures leveraging immutable GHCR tags.
* 🧠 **[ML Model Card](docs/architecture/model-card.md)** — Isolation Forest training baselines, statistical thresholds, and limitations.
* 🔒 **[Threat Model](docs/architecture/threat-model.md)** — STRIDE analysis and mitigated attack vectors.

---

## 🛠️ Technology Stack

- **Cloud API:** Node.js, Fastify, Prisma (MySQL 8)
- **Edge Node:** Python 3.11, FastAPI, Paho-MQTT, Scikit-learn
- **Frontend:** Next.js (React), TailwindCSS
- **Infrastructure:** Docker Compose, Nginx, Mosquitto
- **DevSecOps:** GitHub Actions, GHCR, Gitleaks, Trivy
- **Observability:** Prometheus, Grafana, Alertmanager

---
*EdgeSentinel was architected and built as a comprehensive demonstration of Full-Stack Platform Engineering.*
