# ADR 003: Deterministic Docker Orchestration

**Status**: Accepted  
**Date**: 2026-09-15  

## Context and Problem Statement
When bringing up the entire distributed stack via `docker compose up`, various services (Edge Node, Simulator, Cloud API) historically crashed or entered cyclic restart loops due to inherent race conditions. For instance, the Edge Node would attempt to connect to the MQTT broker before the broker had finished binding to its socket, and the Cloud API would attempt to seed default users into a database that was still initializing.

## Decision
We implemented a strict, deterministic container boot sequence relying exclusively on native **Docker Compose Health Checks** and `depends_on: { condition: service_healthy }`.

### Specific Fixes Discovered During Implementation:

1. **Bypassing Alpine Linux IPv6 Routing Issues**:
   When configuring health checks for the Mosquitto MQTT broker (`nc -z localhost 1883`) and the Fastify Cloud API (`curl -f http://localhost:3000/health`), we encountered continuous failure states. We discovered that Alpine Linux natively resolves `localhost` to both IPv6 (`::1`) and IPv4 (`127.0.0.1`). Because the services were bound exclusively to IPv4, the health probes failed to route. We explicitly hardcoded `127.0.0.1` in the `docker-compose.yml` health checks to bypass this routing conflict entirely.

2. **Mitigating the Prisma Schema Initialization Race Condition**:
   The `cloud-api` dynamically seeds users on startup. However, on a fresh MySQL volume, the underlying tables do not exist. Instead of baking complex bash scripts into the Dockerfile, we documented a strict operational procedure to run `docker compose run --rm cloud-api npx prisma db push` *prior* to bringing up the stack. This cleanly initializes the schema, ensuring the Cloud API boots up flawlessly.

## Consequences
### Positive
- **Rock-Solid Stability**: The environment boots deterministically 100% of the time. Edge services gracefully wait for a confirmed `Healthy` signal from both Mosquitto and the Cloud API before executing a single line of application code.
- **No Wrapper Scripts**: We achieved this stability using purely native declarative YAML, avoiding fragile `wait-for-it.sh` shell scripts inside our Docker images.

### Negative
- **Slower Boot Times**: Local environment startup takes slightly longer, as dependent containers are completely paused until upstream health checks pass their minimum start periods and polling intervals.
