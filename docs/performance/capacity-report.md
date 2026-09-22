# EdgeSentinel Capacity & Load Test Report

**Date:** YYYY-MM-DD
**Tested By:** [Name]
**Target Environment:** [Local Docker Compose / Staging / Production]

## 1. Test Methodology
Describe how the load test was conducted.
* **Tool Used:** k6 (via Docker container)
* **Script:** `tests/load/telemetry-ingestion.js`
* **Scenario:** Simulated 25 concurrent edge devices constantly pushing telemetry events over a 2-minute period.
* **Endpoints Tested:** `POST /api/v1/telemetry`

## 2. Target Service Level Objectives (SLOs)
The system must satisfy these thresholds under load:
* **Latency (p99):** < 500ms
* **Error Rate:** < 1% (HTTP 500s or timeouts)

## 3. Observed Results
Record the results from the k6 output here.

| Metric | Target SLO | Observed Result | Status (Pass/Fail) |
| :--- | :--- | :--- | :--- |
| **Throughput (Requests/sec)** | N/A | [e.g., 25 req/s] | N/A |
| **Latency (p95)** | N/A | [e.g., 120ms] | N/A |
| **Latency (p99)** | < 500ms | [e.g., 180ms] | **[PASS]** |
| **Error Rate** | < 1% | [e.g., 0.0%] | **[PASS]** |

## 4. Resource Utilization
Record the peak CPU and Memory usage of the core containers during the test (using `docker stats`).

* **cloud-api Container:** 
  * CPU Peak: [e.g., 15%]
  * Memory Peak: [e.g., 120MB]
* **mysql Container:**
  * CPU Peak: [e.g., 8%]
  * Memory Peak: [e.g., 400MB]

## 5. Identified Bottlenecks & Optimizations
* **Database Indexing:** We preemptively added descending timestamp composite indexes to `Telemetry` to prevent full table scans on the `GET /api/v1/telemetry` endpoint as the table grows into the millions of rows.
* **[Add any other bottlenecks discovered during testing here]**
