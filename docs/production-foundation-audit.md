# EdgeSentinel — Production Foundation Audit & Engineering Plan

> **Audit Date:** 2026-09-16
> **Auditor:** Full source-code inspection (not documentation review)
> **Scope:** All services, configuration, infrastructure, tests, CI

---

## Current Project Description

> **A functioning distributed edge-cloud prototype with persistent cloud storage, edge-side anomaly detection, offline buffering, adaptive routing, authentication, observability foundations, and automated container builds — but not yet a deployment-ready application.**

The project has already crossed the "toy project" stage. Several meaningful engineering concepts are present and working:

| Concept | Status |
|---|---|
| MQTT-based device communication | ✅ working |
| Edge processing + ML inference (Isolation Forest) | ✅ working |
| Offline-first architecture (SQLite outbox) | ✅ working |
| Retry / exponential backoff | ✅ working |
| Idempotent cloud ingestion (`event_id`) | ✅ working |
| MySQL persistence | ✅ working |
| JWT / RBAC authentication | ✅ working |
| Server-Sent Events (SSE) real-time feed | ✅ working |
| Docker Compose orchestration | ✅ working |
| Prometheus + Grafana (foundations) | ✅ working |
| CI (build validation) | ✅ working |
| Fault injection lab | ✅ working |

The **production engineering foundation is incomplete**. The audit below identifies what is wrong and why. The phase plan at the end of this document defines the correct order of work.

**Verdict:** The system is not production-ready. Several correctness problems, security gaps, and infrastructure omissions must be resolved before any deployment.

---

## Current Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Developer Machine                         │
│  apps/web (Next.js 16, Tailwind)  ─────► localhost:3000  (API)  │
└──────────────────────────────────────────────────────────────────┘

Docker Network: edgesentinel-network

┌─────────────────┐     MQTT      ┌──────────────────────┐
│   simulator     │ ────────────► │  mosquitto (MQTT)    │
│  (Python, paho) │               │  eclipse-mosquitto:2 │
│  port: (none)   │               │  port: 1883          │
└─────────────────┘               └──────────┬───────────┘
                                             │ MQTT subscribe
                                             ▼
                                  ┌──────────────────────┐       SQLite outbox.db
                                  │   edge-service       │ ──── (file inside container,
                                  │  (FastAPI + uvicorn) │       no volume mount)
                                  │  port: 8000          │
                                  │  + IsolationForest   │
                                  └──────────┬───────────┘
                                             │ HTTP POST (Bearer JWT)
                                             ▼
                                  ┌──────────────────────┐
                                  │   cloud-api          │
                                  │  (Fastify + Prisma)  │
                                  │  port: 3000          │
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │  mysql:8.0           │
                                  │  port: 3306          │
                                  │  (no persistent vol) │
                                  └──────────────────────┘

Observability:
  prometheus:9090  ← scrapes cloud-api:3000/metrics and edge-service:8000/metrics
  grafana:3002     ← Prometheus datasource auto-provisioned; zero dashboards

Web app NOT containerised — runs on developer machine only (npm run dev).
```

### Service Inventory

| Service | Technology | Port | Responsibility | Key Dependencies |
|---|---|---|---|---|
| **web** | Next.js 16 / React 19 / Tailwind 4 | 3000 (local dev only) | Dashboard UI, login, SSE stream, fault lab | cloud-api:3000, edge:8000 |
| **cloud-api** | Fastify 5, Prisma 6, Node 22 | 3000 | REST API, JWT auth, telemetry ingestion, SSE broadcast | mysql |
| **edge-service** | FastAPI, uvicorn, Python 3.11 | 8000 | MQTT subscriber, ML inference, SQLite outbox, cloud sync | mosquitto, cloud-api |
| **simulator** | Python 3.11, paho-mqtt | — | Publishes random telemetry every 5 s | mosquitto |
| **mosquitto** | eclipse-mosquitto:2.0 | 1883 | MQTT broker | — |
| **mysql** | mysql:8.0 | 3306 | Primary cloud data store | — |
| **prometheus** | prom/prometheus (untagged) | 9090 | Metrics scraping | cloud-api, edge-service |
| **grafana** | grafana/grafana (untagged) | 3002 | Metrics visualisation | prometheus |

---

## Database

### MySQL Schema (confirmed against live running container)

Live record counts: **telemetry: 731 rows, anomaly_events: 731 rows, devices: 1 row**. Data IS persisting to MySQL correctly.

**`telemetry`**

| Column | Type | Key |
|---|---|---|
| id | varchar(191) | PK |
| event_id | varchar(191) | UNIQUE |
| device_id | varchar(191) | FK → devices, IDX |
| temperature | double | |
| humidity | double | |
| vibration | double | |
| pressure | double | |
| machine_state | varchar(191) | |
| timestamp | datetime(3) | |
| created_at | datetime(3) | |

**`anomaly_events`**

| Column | Type | Key |
|---|---|---|
| id | varchar(191) | PK |
| telemetry_id | varchar(191) | FK → telemetry (CASCADE), IDX |
| severity | varchar(191) | |
| score | double | |
| decision | varchar(191) | |
| model_version | varchar(191) | |
| created_at | datetime(3) | |

**What works:**
- `event_id` UNIQUE index — duplicate events rejected at DB level
- Foreign keys with `ON DELETE CASCADE` correctly defined
- `connectOrCreate` on device prevents duplicate device rows

**Problems:**

1. **No MySQL persistent volume** — `docker-compose.yml` mounts no named volume. Every `docker compose down` wipes all telemetry records and user accounts.

2. **Migration file is SQLite DDL** — `prisma/migrations/.../migration.sql` uses SQLite syntax (`TEXT NOT NULL PRIMARY KEY`, `DATETIME`, `REAL`). Generated against the old SQLite provider. Will fail on `prisma migrate deploy` against MySQL.

3. **`apps/api/.env` has `DATABASE_URL="file:./dev.db"`** — Running the API locally without overriding this env var silently connects to SQLite, not MySQL.

4. **`prisma/dev.db` (421 KB) committed to the repository** — Real SQLite development database in version control.

5. **No telemetry query pagination** — `GET /api/v1/telemetry` returns an in-memory array capped at 50 events. No database-backed pagination, date filtering, or device filtering.

6. **`anomaly_events` created for every event including NORMAL** — 731 telemetry rows = 731 anomaly rows. Inflates storage; anomaly table has no semantic meaning for NORMAL-severity events.

---

## Authentication

### Actual flow

```
POST /api/v1/auth/login
  → Zod validates { email, password }
  → prisma.user.findUnique({ where: { email } })
  → bcrypt.compare(password, user.password_hash)
  → fastify.jwt.sign({ userId, email, role })    ← NO expiresIn
  → 200 { data: { token, user }, token }         ← token appears TWICE
```

**What works:**
- bcrypt password hashing (cost factor 10) ✅
- JWT secret absence = server startup crash (enforced at boot) ✅
- JWT verified on every protected route ✅
- RBAC (ADMIN/OPERATOR/VIEWER) enforced per route ✅
- Invalid/missing token → 401; wrong role → 403 ✅

**Problems:**

1. **JWT has no expiry** — `jwt.sign(payload)` called with no `expiresIn`. Tokens issued today are valid forever. Stolen tokens cannot be invalidated.

2. **Token appears twice in login response** — `{ data: { token }, token }`. The web client reads the root-level `token`; `data.token` is the unused duplicate.

3. **Development password hardcoded in source** — `auth.service.ts` line 62: `bcrypt.hash('admin123', 10)`. `prisma/seed.ts` line 8: same. No deployment-time mechanism to change this.

4. **`seedDefaultUsersIfEmpty` creates 4 accounts** — Besides `admin@edgesentinel.local` it also creates bare `admin` (no domain), `operator@edgesentinel.local`, `viewer@edgesentinel.local`. Undocumented and inconsistent.

5. **No token refresh endpoint** — No `POST /api/v1/auth/refresh`. Moot while tokens never expire, but both issues must be solved together.

6. **SSE token in URL** — `GET /api/v1/telemetry/stream?token=<jwt>` — token visible in server access logs and browser history. Known `EventSource` limitation; should be documented.

---

## Authorization

**What works:**
- POST `/telemetry` requires OPERATOR or ADMIN ✅
- GET `/telemetry` requires VIEWER, OPERATOR, or ADMIN ✅
- Role embedded in JWT — no extra DB call per request ✅

**Problems:**

1. **`requireRole` calls `jwtVerify()` twice** — `authenticate` already verified the JWT; `requireRole` verifies it again. Redundant work on every protected request.

2. **Role is a free-form string** — No enum enforcement. `'Admin'` ≠ `'ADMIN'` and silently fails authorization.

3. **No `GET /api/v1/me`** — Web client cannot show who is logged in or validate a stored token after page refresh.

---

## Configuration

### Complete Secret and Credential Inventory

| Location | Key | Classification |
|---|---|---|
| `docker-compose.yml:52` | `API_PASSWORD=admin123` (plain text) | **SECURITY RISK** |
| `docker-compose.yml:72` | `JWT_SECRET=your-super-secret-jwt-key-here` | **SECURITY RISK** |
| `docker-compose.yml:27-30` | `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` from `.env` = `secret` | **SECURITY RISK** |
| `.env:3` | `MYSQL_PASSWORD=secret` | **SECURITY RISK** |
| `.env:8` | `DATABASE_URL=mysql://admin:secret@...` | **SECURITY RISK** |
| `apps/api/.env:4` | `JWT_SECRET=your-super-secret-jwt-key-here` | **SECURITY RISK** |
| `apps/api/.env:3` | `DATABASE_URL="file:./dev.db"` (wrong environment) | **DEVELOPMENT ONLY** |
| `apps/api/.env.example:4` | `JWT_SECRET=your-super-secret-jwt-key-here` | **DEVELOPMENT ONLY** |
| `services/edge/.env:3` | `API_PASSWORD=admin123` | **SECURITY RISK** |
| `services/edge/app/config/settings.py:30` | `API_PASSWORD` default hardcoded = `"admin123"` | **SECURITY RISK** |
| `apps/api/src/modules/auth/auth.service.ts:62` | seed password `'admin123'` in source | **SECURITY RISK** |
| `apps/api/prisma/seed.ts:8` | seed password `'admin123'` in source | **SECURITY RISK** |

The `.gitignore` correctly excludes `.env*` files. However `apps/api/.env` exists locally with wrong values. `docker-compose.yml` hardcodes both the JWT secret and the edge API password in plain text — committed to Git.

---

## Docker

### API Dockerfile

| Check | Result |
|---|---|
| Multi-stage build (builder + runner) | ✅ |
| `node:22-slim` base | ✅ |
| Pinned SHA digest | ❌ |
| Non-root (`USER node`) | ✅ |
| curl for healthcheck | ✅ |
| `.env` not copied | ✅ |
| `npm ci` (not `npm install`) | ❌ — not lockfile-reproducible |
| devDeps (`tsx`, `prisma`, `typescript`) in runner | ⚠️ — copied via `COPY --from=builder` |

### Edge Dockerfile

| Check | Result |
|---|---|
| `python:3.11-slim` | ✅ |
| Pinned SHA digest | ❌ |
| Non-root (`appuser`) | ✅ |
| App dir owned by appuser | ✅ |
| `--no-cache-dir` | ✅ |
| Version pins in requirements.txt | ❌ — none |
| SQLite outbox volume | ❌ — file inside container, lost on restart |

### Simulator Dockerfile

| Check | Result |
|---|---|
| `python:3.11-slim` | ✅ |
| Non-root user | ❌ — no USER directive |
| Version pins | ❌ |

### `docker-compose.yml`

| Check | Result |
|---|---|
| MySQL healthcheck (`mysqladmin ping`) | ✅ |
| Mosquitto healthcheck (`nc -z 1883`) | ✅ |
| API healthcheck (`curl /health`) | ✅ |
| `depends_on` with health conditions | ✅ |
| `restart: unless-stopped` all services | ✅ |
| MySQL persistent volume | ❌ **MISSING** |
| MQTT persistent volume | ❌ **MISSING** |
| Prometheus persistent volume | ❌ **MISSING** |
| Edge SQLite volume | ❌ **MISSING** |
| Web service | ❌ **MISSING** — web not in compose |
| `version: '3.8'` (obsolete) | ⚠️ generates warning every run |
| Secrets management | ❌ plain-text env vars only |
| Prometheus image tagged | ❌ — `prom/prometheus` (no version) |
| Grafana image tagged | ❌ — `grafana/grafana` (no version) |

---

## API

### Endpoint Inventory

| Method | Path | Auth | Role | Validation | DB Action |
|---|---|---|---|---|---|
| `GET` | `/health` | No | — | — | None (does NOT probe MySQL) |
| `GET` | `/metrics` | No | — | — | Prometheus export |
| `POST` | `/api/v1/auth/login` | No | — | Zod (email, password) | User lookup + bcrypt compare |
| `POST` | `/api/v1/telemetry` | JWT | OPERATOR, ADMIN | Zod (full schema) | INSERT telemetry + device upsert + optional anomaly |
| `GET` | `/api/v1/telemetry` | JWT | VIEWER+ | — | **In-memory array only — NOT the database** |
| `GET` | `/api/v1/telemetry/stream` | JWT or `?token=` | — | — | SSE broadcast, no DB |

**What works:**
- Consistent `/api/v1` versioned prefix ✅
- Zod validation with field-level error details ✅
- Database-backed idempotency via `event_id` UNIQUE constraint ✅
- 500 errors return safe messages — no stack traces exposed ✅

**Problems:**

1. **`GET /api/v1/telemetry` reads in-memory array, not MySQL** — `recentEvents` is a module-level array capped at 50. Empty after every API restart. Dashboard shows nothing even with 731 records in MySQL.

2. **`recentEvents` populated before duplicate check** — `recentEvents.unshift()` runs unconditionally before `processTelemetry()` determines duplicate status.

3. **No `GET /api/v1/devices`** — Devices are implicitly created but cannot be listed.

4. **No rate limiting on login** — Unlimited password attempts.

5. **`/metrics` unauthenticated** — Request counts, durations, Node.js runtime data exposed publicly.

---

## Edge

### Telemetry Flow (traced end-to-end)

```
1. simulator → MQTT: edgesentinel/devices/DEVICE-001/telemetry (every 5 s)

2. edge on_message() [paho MQTT thread]:
   - parse JSON
   - inference.get_anomaly_score(temp, humidity, vibration, pressure)
   - inference.classify_severity(score) → NORMAL / WARNING / CRITICAL
   - edge_cpu = random.uniform(10.0, 90.0)          ← SIMULATED, not real
   - network_latency = random.uniform(15.0, 75.0)   ← SIMULATED, not real
   - decision_engine.evaluate_routing_policy(severity, latency, cpu)
   - event_id = payload.get("eventId") or uuid4()
   - outbox_repo.insert_event(event_id, payload)     ← SQLite BEGIN IMMEDIATE

3. SyncWorker asyncio loop (polls every 1.0 s):
   - fetch_pending_batch(limit=20)  ORDER BY id ASC (FIFO)
   - mark_processing(batch_ids)
   - POST /api/v1/telemetry with Bearer token
   - 200/201 → mark_sent(), reset backoff to 2 s
   - 5xx / network error → record_failure(), exponential backoff 2→4→8→...→60 s
   - 4xx → record_failure(), no backoff, continue to next event
   - 401 → re-authenticate once, retry same event
```

**What works:**
- MQTT ingest never blocks on cloud latency ✅
- SQLite WAL mode + `BEGIN IMMEDIATE` transactions ✅
- Thread-safe `threading.Lock()` on all outbox operations ✅
- `recover_stale_processing()` on startup ✅
- Graceful shutdown WAL checkpoint ✅
- Exponential backoff capped at 60 s ✅
- Per-event `max_attempts=5` ✅
- 401 auto-re-authentication ✅

**Problems:**

1. **SQLite outbox has no volume** — Container restart destroys `outbox.db`. All PENDING events lost.

2. **At-least-once delivery gap** — If edge crashes after API returns 201 but before `mark_sent()`, event remains PENDING and will retry. The API's `event_id` UNIQUE constraint prevents a duplicate record in MySQL. Acceptable, but undocumented.

3. **`main.py`, `inference.py`, `decision_engine.py` at repo root** — Imported as bare top-level modules (`import inference`). Not proper Python packages. Fragile structure.

4. **`edge_cpu` and `network_latency` are `random` values** — Decision engine routing decisions are based on simulated metrics, not real system state.

5. **MQTT retries only 3 × 2 s on startup** — Gives up after 6 s total. Edge runs with no MQTT subscription if mosquitto is slow.

6. **Single device only** — Simulator always publishes as `DEVICE-001`.

---

## ML

### Model Type: TRAINING MODEL (synthetic data, trains at import)

```python
# inference.py
model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)

def train_dummy_model():
    np.random.seed(42)
    normal_data = np.column_stack([
        np.random.uniform(20.0, 80.0, 200),    # temperature
        np.random.uniform(30.0, 70.0, 200),    # humidity
        np.random.uniform(0.1, 2.5, 200),      # vibration
        np.random.uniform(980.0, 1025.0, 200)  # pressure
    ])
    model.fit(normal_data)

train_dummy_model()  # runs at module import
```

**What works:**
- `random_state=42` + `np.random.seed(42)` → deterministic model across restarts ✅
- Trains once at import, not per-inference ✅

**Problems:**

1. **Model is a demo** — Trained on 200 synthetic random samples. Not calibrated to any real industrial data. Anomaly scores and severity labels have no ground truth relationship to real failure modes.

2. **`model_version` hardcoded as `'v1.0.0'`** — In `telemetry.service.ts`. Does not reflect any actual model state.

3. **No model persistence** — No `joblib.dump()`. A real trained model could not be deployed this way.

4. **Severity thresholds are undocumented magic numbers** — `>= -0.08` = NORMAL, `>= -0.12` = WARNING, else CRITICAL. No justification.

5. **Decision engine is counterintuitive** — Returns `"EDGE"` when severity is CRITICAL or latency > 200 ms, meaning critical anomalies are processed locally rather than forwarded to the cloud. Not necessarily wrong, but undocumented and surprising.

---

## Observability

### Prometheus Metrics

| Metric | Source | Description |
|---|---|---|
| `cloud_events_received_total` | cloud-api | Counter: each telemetry POST |
| `events_processed_total` | edge-service | Counter: each MQTT message |
| `http_request_duration_seconds` | edge-service | Auto-instrumented by prometheus-fastapi-instrumentator |
| Node.js defaults (heap, GC, event loop) | cloud-api | prom-client defaults |

**Grafana:** Auto-provisioned Prometheus datasource. Zero dashboards. Opens to a blank workspace.

**What works:**
- Both services expose `/metrics` ✅
- Prometheus scrape config targets both correctly ✅
- Edge uses structured log format with timestamps and logger names ✅
- API uses Fastify JSON logging ✅
- Event IDs appear in edge logs ✅

**Problems:**

1. **Zero Grafana dashboards** — Observability stack requires complete manual setup.
2. **Only one API business metric** — No metrics for: auth failures, duplicate rate, anomaly severity histogram, SSE client count, DB errors.
3. **Prometheus has no persistent volume** — All metric history lost on container restart.
4. **`/metrics` unauthenticated** on both services.
5. **No request correlation IDs** — Cannot link a Fastify request to the Prisma query it triggers.
6. **`sqlalchemy` in `requirements.txt` but never used** — Edge uses raw `sqlite3` from stdlib.

---

## Testing

### Existing Tests

| File | Runner | Coverage |
|---|---|---|
| `test_outbox_worker.py` (repo root) | `python test_outbox_worker.py` (manual only) | SQLite outbox CRUD, state machine, concurrent writes, SyncWorker with mock httpx transport, exponential backoff, FIFO drain |

**What works:**
- Tests real behavior with real SQLite, real threads, real asyncio ✅
- Uses temp files — does not touch production data ✅
- `httpx.AsyncBaseTransport` mock is correct and meaningful ✅

**Problems:**

1. **No test runner** — Uses `asyncio.run(run_tests())` under `__main__`. Cannot be discovered or run by pytest.
2. **Zero API tests** — No tests for any Fastify route: login, telemetry POST, auth failure, role enforcement, duplicate events, validation errors.
3. **Zero ML unit tests** — `inference.py` and `decision_engine.py` have no tests.
4. **Zero web app tests**.
5. **CI does not run any tests** — CI can pass on a completely broken codebase.
6. **Missing critical cases:** JWT expiry enforcement, VIEWER cannot POST telemetry, MySQL unreachable, SQLite file missing.

---

## CI/CD

### Current CI (`.github/workflows/ci.yml`)

**Triggers:** push to `main`, PR to `main`

**Job 1:** installs Node 20 + `npm install` in `apps/api`; installs Python 3.11 + edge + simulator pip deps.
**Job 2:** builds three Docker images; runs `docker compose config`.

**What CI validates:** dependencies install, images build, compose file is syntactically valid.

**What CI does NOT validate:**
- No tests run ❌
- No TypeScript type checking ❌
- No ESLint ❌
- No Python linting ❌
- `apps/web` not built or checked ❌
- No integration test ❌
- No `prisma migrate deploy` validation ❌
- Node 20 in CI vs Node 22 in Dockerfile ❌
- Two jobs are parallel with no declared dependency ❌

---

## Reliability — Scenario Analysis

| Scenario | Result | Notes |
|---|---|---|
| A — API unavailable | ✅ Works | Outbox buffers; SyncWorker backs off (2→60 s); drains on recovery |
| B — API returns 500 | ✅ Works | `record_failure()` called; backoff applied; max 5 attempts |
| C — API returns 401 | ✅ Works | Re-authenticates once; retries; if re-auth fails → backoff |
| D — MySQL unavailable | ⚠️ Partial | API returns 500 on DB calls. `/health` returns healthy regardless — does not probe MySQL |
| E — MQTT unavailable | ⚠️ Partial | Edge retries 3 × 2 s on startup then gives up. HTTP `/telemetry` on port 8000 still works as fallback |
| F — Edge restarts | ❌ Broken | `outbox.db` inside container; no volume; all PENDING events lost |
| G — MySQL restarts | ✅ Works | Prisma reconnects automatically. Data intact if still running; lost if `docker compose down` used |
| H — Duplicate event | ✅ Works | `event_id` UNIQUE in MySQL; `processTelemetry()` returns `isDuplicate: true` with 200; outbox uses `INSERT OR IGNORE` |

---

## Security

| ID | Finding | Severity |
|---|---|---|
| S-01 | `JWT_SECRET=your-super-secret-jwt-key-here` hardcoded in `docker-compose.yml` | **CRITICAL** |
| S-02 | JWT tokens have no expiry — stolen tokens are permanently valid | **CRITICAL** |
| S-03 | `admin123` hardcoded in source code (`auth.service.ts`, `seed.ts`) and compose | **HIGH** |
| S-04 | `MYSQL_PASSWORD=secret` — trivially guessable | **HIGH** |
| S-05 | `POST /faults` on edge port 8000 is unauthenticated — any caller can disable outbox sync | **HIGH** |
| S-06 | No rate limiting on login — brute force unrestricted | **HIGH** |
| S-07 | `allow_anonymous true` in mosquitto — any MQTT client can publish to any topic | **HIGH** |
| S-08 | `/metrics` endpoints unauthenticated on both services | **MEDIUM** |
| S-09 | API CORS `origin: '*'` | **MEDIUM** |
| S-10 | Edge CORS `allow_origins=["*"]` | **MEDIUM** |
| S-11 | `prisma/dev.db` (421 KB) committed to repository | **MEDIUM** |
| S-12 | `apps/api/.env` with wrong DATABASE_URL and placeholder JWT secret present on disk | **MEDIUM** |
| S-13 | No security response headers (HSTS, X-Content-Type-Options, X-Frame-Options) | **MEDIUM** |
| S-14 | SQL injection: Prisma ORM parameterizes all queries — no risk found | **INFORMATIONAL** |
| S-15 | `requireRole` calls `jwtVerify()` twice (redundant, not a security gap) | **LOW** |
| S-16 | JWT in SSE URL query param appears in access logs | **LOW** |
| S-17 | bcrypt cost factor 10 — acceptable minimum | **INFORMATIONAL** |

---

## Findings Table

| ID | Area | Finding | Priority | Recommendation |
|---|---|---|---|---|
| F-01 | Docker | No MySQL persistent volume — data lost on `down` | **P0** | Add named volume for `/var/lib/mysql` |
| F-02 | Docker | No edge SQLite volume — outbox lost on restart | **P0** | Mount named volume to `/app/outbox.db` |
| F-03 | Security | JWT secret hardcoded in `docker-compose.yml` | **P0** | Require `JWT_SECRET` env var; no default |
| F-04 | Security | JWT tokens have no expiry | **P0** | Add `expiresIn: '8h'` to `jwt.sign()` |
| F-05 | API | `GET /api/v1/telemetry` reads in-memory array, not MySQL | **P0** | Replace with `prisma.telemetry.findMany()` + pagination |
| F-06 | Security | No rate limiting on login | **P0** | Add `@fastify/rate-limit` (5 req/min per IP on login) |
| F-07 | Security | `POST /faults` on edge is unauthenticated | **P1** | Require `EDGE_ADMIN_TOKEN` header |
| F-08 | Database | Migration SQL is SQLite DDL — will fail against MySQL | **P1** | Regenerate migration with MySQL provider |
| F-09 | Security | `admin123` hardcoded in source | **P1** | Use `SEED_ADMIN_PASSWORD` env var; crash if unset |
| F-10 | Config | `apps/api/.env` has wrong DATABASE_URL | **P1** | Fix or delete |
| F-11 | Database | `prisma/dev.db` committed to repository | **P1** | Add `*.db` to gitignore; delete file |
| F-12 | CI | CI does not run any tests | **P1** | Add outbox test + API smoke test |
| F-13 | Testing | Zero tests for any API route | **P1** | Add Fastify injection tests |
| F-14 | Docker | Prometheus and Grafana images untagged | **P1** | Pin to specific versions |
| F-15 | Docker | `npm install` instead of `npm ci` in API Dockerfile | **P1** | Use `npm ci` |
| F-16 | Edge | Python requirements.txt has no version pins | **P1** | Pin all dependencies |
| F-17 | API | `/health` does not probe MySQL | **P1** | Add `prisma.$queryRaw\`SELECT 1\`` |
| F-18 | Testing | `test_outbox_worker.py` not runnable by pytest | **P2** | Migrate to `pytest` + `pytest-asyncio` |
| F-19 | CI | Node 20 in CI vs Node 22 in Dockerfile | **P2** | Align to Node 22 |
| F-20 | API | Token appears twice in login response | **P2** | Remove root-level `token` field |
| F-21 | Auth | No JWT refresh endpoint | **P2** | Add after fixing expiry (F-04) |
| F-22 | API | `requireRole` calls `jwtVerify()` twice | **P2** | Remove redundant call |
| F-23 | Docker | `version: '3.8'` in compose is obsolete | **P3** | Remove it |
| F-24 | Edge | `sqlalchemy` in requirements but unused | **P3** | Remove it |
| F-25 | Observability | No Grafana dashboards provisioned | **P2** | Provision at least one dashboard via JSON |
| F-26 | Observability | Prometheus has no persistent volume | **P2** | Add named volume |
| F-27 | ML | Model trained on synthetic data | **P2** | Document as demo model; accurate `model_version` |
| F-28 | API | No pagination on `GET /telemetry` | **P2** | Add `limit`/`offset`; query DB not memory |
| F-29 | Security | MQTT broker accepts anonymous connections | **P1** | Add username/password to mosquitto config |
| F-30 | Web | Web app not in docker-compose | **P1** | Add `web` service to compose |

---

## Part 1 Implementation Plan

### P0 — Must fix before any deployment (data loss or critical security)

1. Persistent volumes — MySQL + SQLite outbox
2. Fix `GET /telemetry` to query MySQL with pagination
3. JWT expiry (`expiresIn: '8h'`)
4. JWT secret via env var with no default; remove from compose
5. Rate limit login endpoint
6. Remove `prisma/dev.db` from repository

### P1 — Important for production readiness (ordered)

1. Seed password from `SEED_ADMIN_PASSWORD` env var; crash if unset
2. Fix Prisma migration for MySQL; delete the SQLite migration
3. Authenticate `/faults` endpoint on edge
4. Add MQTT authentication (username/password)
5. Pin all Python and Docker image versions
6. Use `npm ci` in API Dockerfile
7. Fix `/health` to probe MySQL
8. Make CI run tests
9. Containerize web app in docker-compose

### P2 — Valuable improvements

1. Telemetry endpoint pagination
2. Remove redundant `jwtVerify()` in `requireRole`
3. Remove duplicate `token` field from login response
4. Provision Grafana dashboard
5. Persistent volume for Prometheus
6. Migrate outbox test to pytest
7. Write API route tests (Fastify inject)
8. Add API business metrics
9. Add correlation IDs to logs
10. Remove unused `sqlalchemy`

### P3 — Future enhancements

1. JWT refresh endpoint
2. Multiple device simulation
3. Real ML training pipeline with persisted model
4. Security response headers
5. Remove obsolete `version: '3.8'` from compose

---

## Recommended Implementation Order

Derived from the actual codebase state:

```
1.  Persistent volumes (MySQL + SQLite)    ← data integrity first
2.  GET /telemetry reads from MySQL        ← dashboard actually works
3.  JWT expiry                             ← auth is sound
4.  JWT secret + seed password via env     ← no secrets in source or compose
5.  Rate limit login                       ← brute force protection
6.  Remove dev.db from repo               ← clean repository
7.  Fix Prisma migration for MySQL         ← deployable schema
8.  Health check probes MySQL              ← accurate health signal
9.  Authenticate /faults endpoint          ← close unprotected endpoint
10. MQTT authentication                    ← close anonymous broker
11. Pin all dependency versions            ← reproducible builds
12. npm ci in API Dockerfile               ← reproducible builds
13. CI runs tests                          ← CI has meaning
14. Containerize web app                   ← deployable frontend
15. Write API route tests                  ← test coverage for real paths
16. Telemetry endpoint pagination          ← handles production data volume
```
