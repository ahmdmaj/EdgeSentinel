# ADR 002: Database Migration to MySQL

**Status**: Accepted  
**Date**: 2026-09-15  

## Context and Problem Statement
During the initial phases of the project, PostgreSQL 15 was utilized as the primary cloud persistence layer. However, as the project evolved locally, we encountered strict hardware and storage constraints on local development machines. Running multiple hefty PostgreSQL environments and their corresponding write-ahead logs consumed excessive resources, prompting a mid-flight re-evaluation of our relational database engine.

## Decision
We decided to pivot the cloud persistence layer from PostgreSQL 15 to **MySQL 8.0**. 

Because our Cloud API data layer is entirely abstracted behind the **Prisma ORM**, this architectural pivot was executed seamlessly. By updating the Prisma schema provider (`provider = "mysql"`) and adjusting the local `.env` and `docker-compose.yml` configurations, Prisma automatically generated the new migration graphs and MySQL-specific native client binaries without requiring a single rewrite of our application-level business logic.

## Consequences
### Positive
- **Reduced Local Overhead**: MySQL 8.0 fits well within our specific local development hardware limits and storage constraints.
- **Zero Application Refactoring**: The transition proved the value of utilizing an ORM like Prisma, as no SQL queries or TypeScript data controllers required modification.
- **Ecosystem Compatibility**: MySQL integrates flawlessly with our existing tooling, including Prometheus metrics extraction and Fastify server structures.

### Negative
- **Loss of Postgres-Specific Features**: Advanced PostgreSQL-specific data types (e.g., native JSONB indexing) and extensions (e.g., PostGIS, TimescaleDB) are no longer natively available, though standard JSON storage in MySQL 8.0 currently meets our requirements.
