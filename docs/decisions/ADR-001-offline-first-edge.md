# ADR 001: Offline-First Edge Resilience

**Status**: Accepted  
**Date**: 2026-09-15  

## Context and Problem Statement
In industrial IoT deployments, network connectivity between edge facilities and centralized cloud servers is often unstable or intermittent. If the edge service attempts to transmit telemetry data directly over HTTP synchronously, any network outage will result in immediate data loss and dropped sensor readings, severely compromising the anomaly detection lifecycle.

We needed a mechanism to guarantee zero data loss and decouple the high-throughput MQTT ingestion pipeline from the latency-prone cloud synchronization pipeline.

## Decision
We implemented a **local SQLite outbox pattern** on the Python Edge Node. 

All ingested telemetry and computed ML inference scores are immediately written to a local SQLite database (`outbox.db`). A separate, dedicated background thread (the Sync Worker) polls this outbox and securely transmits the events to the Cloud API in batches. 

If the network goes down, the outbox safely buffers the telemetry locally. When connectivity is restored, the worker resumes synchronization using an **exponential backoff** retry strategy.

## Consequences
### Positive
- **Zero Data Loss**: Telemetry data is durably written to disk locally in microseconds before network transmission is even attempted.
- **Decoupled Architecture**: MQTT ingestion threads are completely unblocked from HTTP network latency.
- **Graceful Recovery**: Exponential backoff prevents thundering herd problems when the cloud service recovers from an outage.

### Negative
- **Local Storage Constraints**: The edge device requires sufficient local disk storage to buffer data during prolonged outages.
- **Complexity**: Requires careful transaction management (Write-Ahead Logging / `BEGIN IMMEDIATE`) to prevent SQLite lock contention between the ingestion thread and the sync worker.
