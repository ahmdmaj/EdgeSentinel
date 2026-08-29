EdgeSentinel
Resilient, Offline-First, Adaptive Edge-Cloud Anomaly Detection Platform
Project Type: Full-Stack + Distributed Systems + Edge Computing + AI/ML + DevOps
Primary Portfolio Target: Software Engineering Internship
Development Constraint: Entirely usable with free/open-source technologies and free-tier cloud services
Deployment Target: Publicly accessible cloud frontend/backend + locally/containerized edge environment
Project Status: Architecture and requirements definition
________________________________________
1. Executive Summary
EdgeSentinel is a distributed edge-cloud monitoring and anomaly detection platform designed to demonstrate how modern software systems can continue operating reliably when cloud connectivity is unreliable.
The platform simulates an industrial monitoring environment in which virtual devices continuously generate sensor data such as temperature, vibration, humidity, pressure, and machine-state information.
Instead of sending every sensor reading to the cloud for processing, EdgeSentinel introduces an intelligent edge layer.
The Edge Node:
•	receives sensor data through MQTT,
•	preprocesses the data,
•	performs local ML inference,
•	determines event severity,
•	decides whether processing should remain at the edge or involve the cloud,
•	stores important events locally when connectivity is unavailable,
•	synchronizes queued events with the cloud after connectivity returns.
The cloud provides:
•	centralized device management,
•	incident management,
•	historical analytics,
•	system-wide dashboards,
•	authentication and authorization,
•	policy configuration,
•	model/version information,
•	centralized persistence.
The central engineering challenge is:
How can a distributed AI system make timely anomaly decisions, minimize unnecessary network traffic, and continue operating during cloud/network failures while maintaining reliable synchronization with the cloud?
EdgeSentinel is not intended to claim novel research in edge computing or anomaly detection.
Its value comes from implementing and evaluating a complete, production-style distributed system with measurable trade-offs between edge and cloud processing.
________________________________________
2. Project Vision
The project should demonstrate that the developer can move beyond building ordinary CRUD or AI-powered websites and understand the complete software engineering lifecycle:
Problem
  ↓
Requirements
  ↓
Architecture
  ↓
System Design
  ↓
Implementation
  ↓
Testing
  ↓
Containerization
  ↓
CI/CD
  ↓
Deployment
  ↓
Monitoring
  ↓
Fault Injection
  ↓
Performance Evaluation
  ↓
Documentation
The final system should be understandable, reproducible, testable, deployable, and measurable.
________________________________________
3. Primary Objective
Build a resilient edge-cloud anomaly detection system that:
1.	receives simulated sensor data,
2.	processes sensor data at an edge node,
3.	detects anomalies using a machine-learning model,
4.	makes adaptive edge/cloud processing decisions,
5.	continues operating during network/cloud failure,
6.	persists important events locally,
7.	synchronizes events after recovery,
8.	provides centralized cloud monitoring,
9.	exposes system health and performance metrics,
10.	demonstrates security, testing, deployment, and observability.
________________________________________
4. Secondary Objectives
The project should also demonstrate:
•	REST API development,
•	real-time communication,
•	MQTT messaging,
•	distributed-system concepts,
•	offline-first design,
•	eventual synchronization,
•	idempotency,
•	retry mechanisms,
•	health checks,
•	fault tolerance,
•	Docker containerization,
•	CI/CD,
•	PostgreSQL database design,
•	ML model serving,
•	model versioning,
•	authentication,
•	authorization,
•	audit logging,
•	observability,
•	performance benchmarking.
________________________________________
5. What the Project Is NOT
The following are explicitly outside the initial scope:
•	Real industrial machine control.
•	Safety-critical automation.
•	Real hardware dependency.
•	Blockchain.
•	Kubernetes.
•	Complex microservice architecture.
•	Multiple cloud providers.
•	Kafka.
•	Multiple ML models in the MVP.
•	Large neural networks.
•	Fully autonomous AI agents.
•	Automated physical machine shutdown.
•	Paid AI APIs.
•	Paid cloud infrastructure.
These may be discussed as future extensions, but they should not be allowed to expand the MVP unnecessarily.
________________________________________
6. Core Engineering Problem
A conventional cloud-only monitoring architecture looks like:
Device
  ↓
Internet
  ↓
Cloud
  ↓
ML inference
  ↓
Result
This creates several problems:
•	network latency,
•	bandwidth consumption,
•	cloud dependency,
•	failure during connectivity loss,
•	increased response time for urgent events.
EdgeSentinel introduces:
Device
  ↓
MQTT
  ↓
Edge Node
  ↓
Local ML inference
  ↓
Decision
  ↓
Cloud synchronization
The system should be able to continue operating even when the cloud is unavailable.
________________________________________
7. Central Project Differentiator
The main differentiating feature is:
Adaptive Edge-Cloud Processing
The system should not permanently use either edge or cloud processing.
Instead, a decision engine determines the appropriate processing strategy according to current conditions.
Possible inputs:
•	network availability,
•	network latency,
•	edge CPU utilization,
•	edge memory utilization,
•	model confidence,
•	event severity,
•	payload size,
•	cloud availability,
•	processing requirements.
Possible decisions:
EDGE
CLOUD
HYBRID
Example:
Network unavailable
        ↓
EDGE

Critical event
        ↓
EDGE FIRST + CLOUD SYNC

Low model confidence
        ↓
CLOUD / HYBRID

Edge CPU overloaded
        ↓
CLOUD if available

Normal event + stable network
        ↓
EDGE + periodic summary
Every adaptive decision should optionally record:
decision
reason
timestamp
network state
edge resource state
model confidence
This allows the system's behavior to be explained and evaluated.
________________________________________
8. Main System Actors
8.1 Administrator
Can:
•	log in,
•	view system health,
•	manage devices,
•	view incidents,
•	view edge nodes,
•	configure processing policies,
•	inspect audit logs,
•	inspect system metrics,
•	trigger fault simulations.
8.2 Operations User
Can:
•	view registered devices,
•	monitor sensor activity,
•	view incidents,
•	inspect anomaly details,
•	view historical information,
•	monitor edge-node health.
8.3 Edge Node
Acts as a distributed processing gateway.
Responsibilities:
•	receive sensor data,
•	validate data,
•	preprocess data,
•	perform ML inference,
•	classify anomalies,
•	execute routing policy,
•	persist offline events,
•	synchronize with cloud,
•	expose health information.
8.4 Device Simulator
Simulates industrial devices.
Responsibilities:
•	generate sensor readings,
•	generate normal conditions,
•	generate abnormal conditions,
•	publish MQTT messages,
•	simulate multiple devices,
•	optionally simulate malformed payloads.
8.5 Cloud Backend
Provides centralized services.
Responsibilities:
•	authentication,
•	device management,
•	incident management,
•	synchronization,
•	persistence,
•	analytics,
•	policy management,
•	API access.
________________________________________
9. High-Level Architecture
                         ┌───────────────────────────┐
                         │      WEB DASHBOARD        │
                         │   Next.js + TypeScript    │
                         │                           │
                         │ Devices                   │
                         │ Incidents                 │
                         │ Live Monitoring           │
                         │ Performance Lab           │
                         │ Fault Injection           │
                         │ System Health             │
                         └─────────────┬─────────────┘
                                       │
                                HTTPS / WebSocket
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │       CLOUD API           │
                         │ Node.js + Fastify         │
                         │                           │
                         │ Authentication            │
                         │ Device Management         │
                         │ Incident Management       │
                         │ Synchronization           │
                         │ Policies                  │
                         │ Analytics                 │
                         └───────┬───────────┬───────┘
                                 │           │
                                 │           │
                                 ▼           ▼
                         ┌────────────┐  ┌───────────┐
                         │ PostgreSQL │  │   Event   │
                         │   Neon     │  │ Processing│
                         └────────────┘  └─────┬─────┘
                                               │
                                               │ MQTT / Secure API
                                               ▼
                         ═════════ EDGE ENVIRONMENT ═════════

                         ┌───────────────────────────┐
                         │       EDGE NODE           │
                         │                           │
                         │ Python + FastAPI          │
                         │ ML Inference              │
                         │ Decision Engine            │
                         │ Local SQLite               │
                         │ Sync Engine                │
                         │ Health Monitor             │
                         └─────────────┬─────────────┘
                                       │
                                      MQTT
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │     DEVICE SIMULATOR      │
                         │                           │
                         │ Temperature               │
                         │ Vibration                 │
                         │ Humidity                  │
                         │ Pressure                  │
                         │ Machine State             │
                         └───────────────────────────┘


                  OBSERVABILITY
                  ┌─────────────────────┐
                  │ Prometheus          │
                  │ Grafana             │
                  │ Structured Logs     │
                  └─────────────────────┘


                  CI/CD
                  GitHub
                     ↓
                  GitHub Actions
                     ↓
                  Test → Build → Scan → Deploy
________________________________________
10. Technology Stack
Frontend
•	Next.js
•	React
•	TypeScript
•	Tailwind CSS or clean custom CSS
•	WebSocket/SSE where appropriate
•	Recharts or another free charting library
Deployment:
•	Vercel Hobby
________________________________________
Cloud Backend
•	Node.js
•	TypeScript
•	Fastify
•	Zod for validation
•	Prisma ORM
•	REST API
•	WebSocket/SSE for real-time dashboard updates
Deployment:
•	Render Free or another suitable free-tier platform.
________________________________________
Edge Service
•	Python
•	FastAPI
•	scikit-learn
•	NumPy
•	pandas
•	SQLite
The edge service should run inside Docker.
________________________________________
Messaging
•	MQTT
•	Eclipse Mosquitto
The MQTT broker should initially run inside the local edge environment rather than relying on a paid managed MQTT service.
________________________________________
Database
Primary cloud database:
•	PostgreSQL
•	Neon Free
Local edge database:
•	SQLite
________________________________________
Machine Learning
Initial model:
•	Isolation Forest
Possible future model:
•	XGBoost
•	Autoencoder
•	supervised classifier
Only one model is required for the MVP.
________________________________________
Containerization
•	Docker
•	Docker Compose
________________________________________
CI/CD
•	GitHub
•	GitHub Actions
Pipeline:
Commit
 ↓
Lint
 ↓
Unit Tests
 ↓
Integration Tests
 ↓
Build
 ↓
Container Build
 ↓
Security Scan
 ↓
Deployment
________________________________________
Observability
•	Prometheus
•	Grafana
•	structured JSON logging
________________________________________
Testing
Frontend:
•	Vitest
•	React Testing Library
Backend:
•	Vitest
•	integration tests
Python:
•	pytest
System:
•	Docker Compose
•	MQTT integration tests
•	fault-injection scenarios
________________________________________
11. Free-Tier Architecture
The project must be designed so that no paid service is required.
Cloud
Vercel
    ↓
Next.js

Render
    ↓
Node.js API

Neon
    ↓
PostgreSQL
Local Edge
Docker Compose

Mosquitto
Edge Service
SQLite
Prometheus
Grafana
Device Simulator
Development
GitHub
GitHub Actions
Docker
VS Code
Python
Node.js
All core functionality must remain operational without paid APIs.
________________________________________
12. Cost Strategy
Target:
$0/month
Mandatory paid services:
NONE
Optional expenses:
•	custom domain,
•	future cloud VM,
•	paid managed monitoring,
•	paid LLM API.
None are required.
Free-tier services may have limitations such as cold starts, storage limits, execution limits, or temporary availability. These limitations must be documented rather than hidden.
________________________________________
13. Device Simulator
The simulator represents industrial devices.
Example device:
DEVICE-001
Sensors:
temperature
humidity
vibration
pressure
machine_state
Normal data:
{
  "deviceId": "DEVICE-001",
  "temperature": 45.2,
  "humidity": 52.1,
  "vibration": 2.1,
  "pressure": 101.3,
  "machineState": "running",
  "timestamp": "..."
}
Abnormal data may contain:
temperature spike
high vibration
pressure drop
combined abnormal conditions
The simulator should allow controlled anomaly generation.
________________________________________
14. MQTT Architecture
Example topic structure:
edgesentinel/
    devices/
        DEVICE-001/
            telemetry
            status
            commands
Example:
edgesentinel/devices/DEVICE-001/telemetry
The edge service subscribes to telemetry topics.
The system should consider:
•	QoS,
•	retained messages where appropriate,
•	reconnection,
•	authentication,
•	topic authorization,
•	duplicate messages,
•	malformed payloads.
________________________________________
15. Edge Processing Pipeline
The edge pipeline:
MQTT Message
     ↓
Validation
     ↓
Normalization
     ↓
Feature Extraction
     ↓
ML Inference
     ↓
Severity Classification
     ↓
Adaptive Decision Engine
     ↓
Local Action / Cloud Transmission
     ↓
Local Persistence if Required
________________________________________
16. ML Pipeline
Training:
Historical Dataset
       ↓
Data Cleaning
       ↓
Feature Engineering
       ↓
Training
       ↓
Evaluation
       ↓
Model Export
       ↓
Edge Deployment
Inference:
Sensor Window
      ↓
Feature Extraction
      ↓
Isolation Forest
      ↓
Anomaly Score
      ↓
Normal / Warning / Critical
Every inference should ideally record:
model version
inference location
inference latency
anomaly score
timestamp
________________________________________
17. Severity Classification
Example:
Normal
Warning
Critical
The exact thresholds should be configurable rather than hard-coded throughout the application.
Example:
anomaly score
     ↓
policy
     ↓
severity
Critical events should receive priority over normal telemetry.
________________________________________
18. Adaptive Decision Engine
The decision engine is one of the core components.
Inputs:
network status
network latency
edge CPU
edge memory
model confidence
event severity
cloud availability
Output:
EDGE
CLOUD
HYBRID
Example policy:
IF network unavailable:
    EDGE

IF severity == CRITICAL:
    EDGE_FIRST

IF model confidence < threshold:
    CLOUD if available

IF edge resource usage > threshold:
    CLOUD if available

IF normal:
    EDGE + periodic summary
The implementation should be policy-driven so the rules can evolve.
________________________________________
19. Offline-First Architecture
This is a critical project feature.
When the cloud is unavailable:
Device
  ↓
MQTT
  ↓
Edge
  ↓
ML
  ↓
SQLite
Events should be stored in a durable local outbox.
Example state:
PENDING
SYNCING
SYNCED
FAILED
________________________________________
20. Synchronization
When connectivity returns:
SQLite Outbox
      ↓
Sync Worker
      ↓
Cloud API
      ↓
Validation
      ↓
Idempotency Check
      ↓
PostgreSQL
      ↓
ACK
      ↓
Mark Local Event SYNCED
The system must avoid duplicate cloud records if the same event is transmitted multiple times.
________________________________________
21. Idempotency
Every event should have a unique identifier.
Example:
eventId:
evt_01JXXXXXXXX
The cloud should recognize duplicate events.
If:
eventId = EVT-001
has already been processed, another submission should not create another incident.
This demonstrates an important distributed-system concept.
________________________________________
22. Retry Strategy
Synchronization failures should use retry logic.
Example:
Attempt 1
 ↓
failure
 ↓
wait
 ↓
Attempt 2
 ↓
failure
 ↓
wait longer
 ↓
Attempt 3
Use exponential backoff with a maximum retry interval.
The system should avoid aggressive retry loops.
________________________________________
23. Cloud Data Model
Core entities:
User
Device
EdgeNode
TelemetrySummary
AnomalyEvent
Incident
ProcessingDecision
ModelVersion
SyncRecord
AuditLog
Possible relationships:
User
 │
 └── manages ── Device

Device
 │
 ├── produces ── AnomalyEvent
 │
 └── assigned to ── EdgeNode

AnomalyEvent
 │
 └── creates ── Incident

AnomalyEvent
 │
 └── processed by ── ModelVersion

AnomalyEvent
 │
 └── has ── ProcessingDecision
________________________________________
24. Edge Database
SQLite should contain only data required for local operation.
Possible tables:
local_events
outbox
device_state
model_metadata
sync_state
The edge database should not become a second full cloud database.
Its purpose is resilience and temporary local state.
________________________________________
25. API Responsibilities
Example REST API areas:
/auth
/devices
/edge-nodes
/events
/incidents
/models
/policies
/metrics
/health
/sync
/audit-logs
Examples:
POST /api/v1/auth/login

GET /api/v1/devices

GET /api/v1/devices/:id

GET /api/v1/incidents

GET /api/v1/incidents/:id

POST /api/v1/sync/events

GET /api/v1/edge-nodes

GET /api/v1/health
API contracts should be documented separately.
________________________________________
26. Real-Time Dashboard
The dashboard should provide:
Overview
Total Devices
Online Devices
Offline Devices
Active Incidents
Critical Incidents
Online Edge Nodes
Live Monitoring
Device
Sensor values
Current state
Last heartbeat
Incidents
Severity
Device
Anomaly score
Timestamp
Processing location
Model version
Status
Edge Nodes
Node status
CPU
Memory
Network
Model version
Last synchronization
Pending events
________________________________________
27. Performance Lab
A dedicated page should compare:
Cloud-only
Edge-only
Adaptive
Metrics:
•	decision latency,
•	inference latency,
•	network bytes,
•	detection precision,
•	detection recall,
•	CPU usage,
•	memory usage,
•	synchronization time,
•	outage behavior.
The values must come from actual experiments.
No fabricated performance claims.
________________________________________
28. Fault Injection Module
A developer/admin interface should allow controlled failures.
Examples:
Simulate Network Failure
Simulate High Latency
Simulate Packet Loss
Restart Edge Service
Restart MQTT Broker
Overload Edge Resources
Send Malformed Payload
Simulate Cloud Failure
This allows the project to demonstrate resilience rather than merely claiming it.
________________________________________
29. Resilience Scenarios
At minimum, test:
Scenario 1 — Normal Operation
Device → Edge → Cloud
Expected:
•	telemetry processed,
•	anomaly detected,
•	cloud updated.
Scenario 2 — Network Failure
Device → Edge
          X Cloud
Expected:
•	edge continues operating,
•	incidents stored locally,
•	no data loss.
Scenario 3 — Recovery
Network restored
      ↓
Outbox synchronization
      ↓
Cloud updated
Expected:
•	events synchronized,
•	duplicates prevented.
Scenario 4 — MQTT Restart
Expected:
•	edge reconnects automatically.
Scenario 5 — Edge Restart
Expected:
•	persisted events survive restart.
Scenario 6 — Duplicate Event
Expected:
•	only one cloud record exists.
Scenario 7 — Malformed Event
Expected:
•	rejected safely,
•	logged,
•	system remains healthy.
________________________________________
30. Observability
Every important service should expose health information.
Example:
GET /health
Response:
{
  "status": "healthy",
  "database": "healthy",
  "mqtt": "healthy",
  "model": "healthy",
  "queue": "healthy"
}
Metrics should include:
events_received_total
events_processed_total
anomalies_detected_total
critical_events_total
inference_latency_ms
cloud_sync_latency_ms
sync_failures_total
mqtt_reconnections_total
outbox_pending_events
api_request_latency
Prometheus collects metrics.
Grafana visualizes them.
________________________________________
31. Logging
Use structured logs.
Example:
{
  "level": "info",
  "service": "edge-service",
  "event": "anomaly_detected",
  "deviceId": "DEVICE-001",
  "severity": "critical",
  "inferenceLocation": "edge",
  "latencyMs": 17
}
Logs should support debugging and incident investigation.
________________________________________
32. Security
Security should be implemented as a focused baseline.
User authentication
Use secure authentication mechanisms.
Authorization
Roles:
ADMIN
OPERATOR
VIEWER
Device authentication
Devices should not be allowed to publish arbitrary data without authentication.
API security
Implement:
•	input validation,
•	rate limiting,
•	authentication,
•	authorization,
•	secure headers,
•	secret management.
MQTT security
Implement appropriate:
•	authentication,
•	topic permissions,
•	restricted publishing/subscription.
Audit logs
Record sensitive operations such as:
user login
device registration
device revocation
policy change
model deployment
manual fault injection
________________________________________
33. Model Versioning
Each deployed ML model should have a version.
Example:
anomaly-detector-v1
anomaly-detector-v2
The edge node should report:
current model
model version
deployment timestamp
Future extension:
Cloud
 ↓
New Model
 ↓
Validate
 ↓
Deploy
 ↓
Edge
 ↓
Health Check
 ↓
Rollback if necessary
Only basic version tracking is required initially.
________________________________________
34. Optional AI Explanation Layer
This is NOT part of the core MVP.
After the anomaly has already been detected, an optional LLM can explain the incident.
Architecture:
ML Model
   ↓
Anomaly
   ↓
Incident
   ↓
Optional AI Explanation
The LLM may explain:
•	what happened,
•	which sensor changed,
•	historical similar events,
•	possible causes,
•	recommended investigation steps.
The LLM must NOT be responsible for determining whether the system is safe.
The deterministic ML/policy layer makes that decision.
Possible implementation:
•	local Ollama model,
•	optional external API.
The core system must work without it.
________________________________________
35. Deployment Architecture
Public Cloud
GitHub
   ↓
GitHub Actions
   ↓
Vercel
   ↓
Next.js frontend
Backend:
GitHub
   ↓
GitHub Actions
   ↓
Render
   ↓
Node.js / Fastify
Database:
Backend
   ↓
Neon
   ↓
PostgreSQL
Edge
Docker Compose
 ├── Mosquitto
 ├── Edge Service
 ├── SQLite
 ├── Device Simulator
 ├── Prometheus
 └── Grafana
The edge environment may run on the developer's laptop initially.
This is intentional: it simulates an on-premise edge gateway.
________________________________________
36. Deployment URLs
Target:
Frontend:
https://<project>.vercel.app

Backend:
https://<project>.<free-host>.app

Database:
Managed PostgreSQL

Edge:
Local Docker environment
A custom domain is optional.
________________________________________
37. Environment Configuration
Never commit secrets.
Example:
.env
.env.local
.env.production
Variables may include:
DATABASE_URL
JWT_SECRET
MQTT_HOST
MQTT_PORT
MQTT_USERNAME
MQTT_PASSWORD
API_BASE_URL
MODEL_PATH
Provide:
.env.example
with placeholder values.
________________________________________
38. Repository Architecture
Recommended monorepo:
edgesentinel/
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── tests/
│   │
│   └── api/
│       ├── src/
│       │   ├── modules/
│       │   ├── middleware/
│       │   ├── plugins/
│       │   ├── config/
│       │   └── server.ts
│       └── tests/
│
├── services/
│   ├── edge/
│   │   ├── app/
│   │   ├── inference/
│   │   ├── decision-engine/
│   │   ├── sync/
│   │   ├── storage/
│   │   └── tests/
│   │
│   └── simulator/
│       ├── devices/
│       ├── scenarios/
│       └── tests/
│
├── packages/
│   ├── shared-types/
│   ├── validation/
│   └── config/
│
├── infrastructure/
│   ├── docker/
│   ├── prometheus/
│   ├── grafana/
│   ├── mqtt/
│   └── compose/
│
├── ml/
│   ├── datasets/
│   ├── training/
│   ├── evaluation/
│   ├── models/
│   └── notebooks/
│
├── docs/
│   ├── requirements/
│   ├── architecture/
│   ├── api/
│   ├── database/
│   ├── security/
│   ├── testing/
│   ├── deployment/
│   ├── observability/
│   ├── decisions/
│   └── evaluation/
│
├── scripts/
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── README.md
└── LICENSE
________________________________________
39. Architecture Decision Records
Important technical decisions should be documented.
Example:
docs/decisions/

ADR-001-use-mqtt.md
ADR-002-use-postgresql.md
ADR-003-edge-inference.md
ADR-004-local-sqlite-outbox.md
ADR-005-adaptive-processing.md
ADR-006-docker-compose.md
ADR-007-free-tier-deployment.md
Each ADR should explain:
Context
Decision
Alternatives
Consequences
________________________________________
40. Testing Strategy
Testing should exist at multiple levels.
Unit Tests
Test:
•	decision engine,
•	anomaly classification,
•	validation,
•	retry logic,
•	synchronization,
•	API services.
Integration Tests
Test:
MQTT → Edge
Edge → Cloud
Cloud → PostgreSQL
End-to-End Tests
Test:
Device
 ↓
MQTT
 ↓
Edge
 ↓
Cloud
 ↓
Database
 ↓
Dashboard
Failure Tests
Test network failures and service restarts.
________________________________________
41. CI/CD
GitHub Actions should execute:
Pull Request
      ↓
Install dependencies
      ↓
Lint
      ↓
Unit tests
      ↓
Integration tests
      ↓
Build
      ↓
Docker build
      ↓
Security scan
Main branch:
Merge
 ↓
Build
 ↓
Deploy frontend
 ↓
Deploy backend
________________________________________
42. Development Phases
Phase 0 — Documentation
Create:
•	problem statement,
•	scope,
•	requirements,
•	architecture,
•	database design,
•	API contract,
•	development plan.
No major coding yet.
________________________________________
Phase 1 — Vertical Slice
Build:
Simulator
 ↓
MQTT
 ↓
Edge
 ↓
Cloud API
 ↓
PostgreSQL
 ↓
Dashboard
One device and one anomaly scenario are enough.
________________________________________
Phase 2 — ML
Implement:
•	dataset,
•	feature extraction,
•	Isolation Forest,
•	anomaly score,
•	severity classification,
•	model version.
________________________________________
Phase 3 — Offline Edge
Implement:
•	SQLite,
•	local event persistence,
•	outbox,
•	retry,
•	synchronization,
•	idempotency.
This is a major milestone.
________________________________________
Phase 4 — Adaptive Processing
Implement:
•	network monitoring,
•	edge resource monitoring,
•	cloud health detection,
•	model confidence,
•	decision policy.
________________________________________
Phase 5 — Dashboard
Implement:
•	live devices,
•	incidents,
•	edge health,
•	anomaly history,
•	processing location,
•	sync status.
________________________________________
Phase 6 — DevOps
Implement:
•	Docker,
•	Docker Compose,
•	GitHub Actions,
•	automated tests,
•	deployment.
________________________________________
Phase 7 — Observability
Implement:
•	Prometheus,
•	Grafana,
•	metrics,
•	structured logging,
•	health checks.
________________________________________
Phase 8 — Security
Implement:
•	authentication,
•	RBAC,
•	device authentication,
•	MQTT authorization,
•	rate limiting,
•	audit logging,
•	secret management.
________________________________________
Phase 9 — Fault Injection
Implement controlled:
•	network failures,
•	latency,
•	packet loss,
•	service restart,
•	malformed messages,
•	resource overload.
________________________________________
Phase 10 — Evaluation
Measure:
•	latency,
•	bandwidth,
•	reliability,
•	synchronization,
•	detection performance,
•	resource consumption.
Create graphs and conclusions.
________________________________________
Phase 11 — Optional Intelligence
Only if the core system is stable:
•	local LLM,
•	incident explanation,
•	model deployment,
•	advanced analytics.
________________________________________
43. MVP Definition
The MVP is complete when the following work:
Device Simulator
       ↓
MQTT
       ↓
Edge Node
       ↓
ML anomaly detection
       ↓
Cloud API
       ↓
PostgreSQL
       ↓
Dashboard
AND:
Cloud unavailable
       ↓
Edge continues
       ↓
SQLite stores events
       ↓
Cloud returns
       ↓
Automatic synchronization
       ↓
No duplicates
AND:
Edge vs Cloud
       ↓
Performance measurements
These are mandatory.
________________________________________
44. V1 Definition
V1 adds:
•	authentication,
•	RBAC,
•	device management,
•	Docker,
•	CI/CD,
•	observability,
•	security,
•	fault injection,
•	production-style documentation.
________________________________________
45. V2 Definition
V2 may include:
•	adaptive routing improvements,
•	model version deployment,
•	model rollback,
•	local LLM explanation,
•	advanced analytics,
•	more sophisticated ML.
V2 should only begin after V1 is stable.
________________________________________
46. Performance Evaluation
The project should answer measurable questions.
Question 1
Does edge inference reduce decision latency?
Question 2
Does selective transmission reduce bandwidth?
Question 3
Can the system continue operating during cloud/network failure?
Question 4
How quickly does synchronization recover after connectivity returns?
Question 5
Does adaptive routing provide a useful compromise between edge and cloud?
Question 6
What is the CPU/memory cost of edge processing?
________________________________________
47. Evaluation Experiments
Run experiments under:
Normal network
Low latency
High latency
Packet loss
Complete network failure
Cloud unavailable
MQTT unavailable
Edge restart
High edge CPU
Low model confidence
Compare:
Cloud-only
Edge-only
Adaptive
Record real measurements.
________________________________________
48. Success Criteria
The project is successful if:
Functional
•	Sensor data reaches the edge.
•	ML detects generated anomalies.
•	Incidents reach the cloud.
•	Dashboard displays incidents.
•	Offline events are persisted.
•	Events synchronize after recovery.
•	Duplicate events are prevented.
Reliability
•	Edge continues during cloud failure.
•	MQTT reconnects after failure.
•	Edge restart does not lose persisted events.
•	Sync retries safely.
Engineering
•	Automated tests exist.
•	Docker Compose reproduces the system.
•	CI/CD works.
•	Health checks work.
•	Metrics are available.
•	Logs are structured.
Security
•	Unauthorized users cannot access protected APIs.
•	Devices require authentication.
•	Roles are enforced.
•	Secrets are not committed.
Evaluation
•	Edge/cloud performance is measured.
•	Fault scenarios are documented.
•	Results are reproducible.
________________________________________
49. Portfolio Demonstration
The final demonstration should not simply show the dashboard.
Use a scenario:
1. Start the system.

2. Show normal device telemetry.

3. Generate an anomaly.

4. Show local edge inference.

5. Show incident on dashboard.

6. Disconnect cloud/network.

7. Generate another critical anomaly.

8. Show edge continues operating.

9. Show event entering SQLite outbox.

10. Restore network.

11. Show automatic synchronization.

12. Demonstrate duplicate protection.

13. Open Performance Lab.

14. Compare Edge vs Cloud vs Adaptive.

15. Open Grafana.

16. Show system metrics.

17. Trigger a fault injection.

18. Show automatic recovery.
This becomes the project's primary portfolio story.
________________________________________
50. Interview Questions the Project Should Enable
The project should allow discussion around:
Architecture
•	Why edge computing?
•	Why MQTT?
•	Why PostgreSQL?
•	Why SQLite at the edge?
•	Why separate Python and TypeScript services?
Distributed systems
•	How do you handle duplicate events?
•	What happens during network failure?
•	How does synchronization work?
•	What consistency model are you using?
ML
•	Why Isolation Forest?
•	How did you evaluate it?
•	What does anomaly score mean?
•	How is model versioning handled?
DevOps
•	Why Docker?
•	What does your CI/CD pipeline do?
•	How are deployments performed?
•	How are failures monitored?
Security
•	How are devices authenticated?
•	How are secrets stored?
•	How do you prevent unauthorized MQTT publishing?
Reliability
•	What happens if the MQTT broker dies?
•	What happens if the edge node restarts?
•	What happens if the cloud is unavailable?
Performance
•	How much latency does edge processing save?
•	How much bandwidth does selective transmission save?
•	When does cloud processing become preferable?
________________________________________
51. Project Philosophy
The project follows these principles:
Principle 1 — Problem before technology
Every technology must have a clear reason.
Principle 2 — Simple before complex
Do not introduce Kubernetes, Kafka, blockchain, or unnecessary microservices without a real requirement.
Principle 3 — Failure is a first-class scenario
The system must be deliberately tested under failure.
Principle 4 — Measure instead of claiming
Performance statements must be supported by experiments.
Principle 5 — Local-first for infrastructure that does not need cloud
MQTT, ML, SQLite, Prometheus, Grafana, and the simulator can remain local.
Principle 6 — Free-first architecture
No paid dependency should be required.
Principle 7 — Production-style, not production-critical
The system demonstrates production engineering principles but is not intended to control real industrial machinery.
________________________________________
52. Technology-to-Problem Mapping
Technology	Why it exists
AI/ML	Detect abnormal sensor behavior
Edge Computing	Reduce latency and cloud dependency
Cloud Computing	Central management and historical analytics
MQTT	Efficient device-to-edge messaging
PostgreSQL	Central persistent storage
SQLite	Offline edge persistence
Docker	Reproducible environments
GitHub Actions	Automated CI/CD
Prometheus	Metrics collection
Grafana	Operational visualization
JWT/RBAC	User security
Device authentication	Secure device communication
WebSocket/SSE	Real-time dashboard updates
Python	ML and edge service
TypeScript	Cloud/application services
Next.js	Web interface
Every technology has a defined responsibility.
________________________________________
53. Technologies Deliberately Excluded
Technology	Reason
Blockchain	No meaningful problem to solve
Kubernetes	Excessive for initial scope
Kafka	MQTT is sufficient
Multiple clouds	Unnecessary complexity
Many microservices	Increases operational overhead
Real hardware	Not required for proof of concept
Paid AI API	Core system should not depend on it
Large LLM	Not required for anomaly detection
Autonomous agents	Not central to the problem
________________________________________
54. Future Extensions
Potential future features:
•	Raspberry Pi edge deployment.
•	Multiple edge locations.
•	Edge-node fleet management.
•	Federated learning.
•	Advanced model lifecycle management.
•	Model drift detection.
•	Local LLM incident assistant.
•	Digital twin visualization.
•	Kubernetes deployment.
•	Cloud-based model training.
•	Advanced security architecture.
•	Blockchain only if a future requirement genuinely benefits from immutable decentralized verification.
These are not part of the current implementation scope.
________________________________________
55. Final Project Definition
Name
EdgeSentinel
Category
Distributed Edge-Cloud AI Platform
Core Problem
Cloud-dependent anomaly detection can suffer from latency, network dependency, and bandwidth consumption.
Solution
A resilient edge-cloud architecture that performs local anomaly detection, dynamically chooses processing strategies, stores events locally during outages, and synchronizes with the cloud after recovery.
Core Innovation/Contribution
Not a claim of novel research.
The engineering contribution is:
An offline-first adaptive edge-cloud anomaly detection architecture with measurable resilience, latency, bandwidth, and synchronization trade-offs.
Core Technologies
Next.js
TypeScript
Node.js
Fastify
Python
FastAPI
scikit-learn
MQTT
Mosquitto
PostgreSQL
Neon
SQLite
Docker
GitHub Actions
Prometheus
Grafana
Vercel
Render
Cost
$0 required.
Primary Portfolio Goal
Demonstrate strong Software Engineering capability across:
Architecture
Backend
Frontend
Distributed Systems
AI/ML Integration
Edge Computing
Cloud
DevOps
Testing
Security
Observability
Reliability
Deployment
Performance Engineering
________________________________________
56. One-Sentence Project Pitch
EdgeSentinel is an offline-first edge-cloud anomaly detection platform that dynamically chooses where AI inference should occur, continues operating during network failures, and reliably synchronizes events with the cloud after recovery.
________________________________________
57. Short Portfolio Description
Designed and deployed a resilient distributed edge-cloud anomaly detection platform using Next.js, TypeScript, Python, MQTT, PostgreSQL, Docker and GitHub Actions. Implemented local ML inference, adaptive edge-cloud routing, offline event persistence, automatic synchronization, fault injection, observability, and performance benchmarking to evaluate latency, bandwidth usage and resilience under network failure.
________________________________________
58. Final Architecture Principle
The final project should always preserve this fundamental relationship:
                 ┌────────────────────┐
                 │       CLOUD        │
                 │                    │
                 │ Management         │
                 │ Analytics          │
                 │ Persistence        │
                 │ Coordination       │
                 └─────────┬──────────┘
                           │
                    Internet / API
                           │
                           ▼
                 ┌────────────────────┐
                 │       EDGE        │
                 │                    │
                 │ Local processing   │
                 │ ML inference       │
                 │ Decision engine    │
                 │ Offline storage    │
                 │ Synchronization    │
                 └─────────┬──────────┘
                           │
                          MQTT
                           │
                           ▼
                 ┌────────────────────┐
                 │     DEVICES       │
                 │                    │
                 │ Sensor simulation  │
                 │ Telemetry          │
                 │ Anomalies          │
                 └────────────────────┘
The cloud should provide centralization.
The edge should provide speed and resilience.
The adaptive engine should determine where computation should occur.
The synchronization system should provide reliable recovery.
The observability system should provide evidence.
The testing system should prove the system actually works under failure.
That is the complete conceptual foundation of EdgeSentinel.

