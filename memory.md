# ShipFaster Dev 3 (Backend) — Memory & Context

_Last Updated: Phase 2 Complete_

---

## Project Overview
**ShipFaster** — Enterprise AI Developer Automation Platform.

5 modules: `scaffolder`, `test_generator`, `docs_generator`, `changelog_generator`, `notebook_to_blog`.

Exposed via: CLI + MCP server + Dashboard UI.
Driven by: FastAPI + Celery + PostgreSQL + Redis + MinIO + Gemini/Claude LLM.

---

## My Role (Dev 3 — Backend / DB / Integration)
**Primary directories**: `/engine/core/`, `/engine/api/`, `/infra/`

**Responsibilities**:
- Database schema (PostgreSQL) + migrations (Alembic)
- Core API (FastAPI) + multi-tenant Auth
- Celery worker (Redis) for async LLM execution
- Centralized `llm_client` wrapper (Gemini primary, Claude fallback)
- Webhook intake (GitHub/CI) + viaSocket dispatch
- Sandbox execution for test validation
- Structured logging, audit trails, observability

**DO NOT**: Implement module logic (Dev 1), Frontend (Dev 2).

---

## Architecture
```
Clean Architecture:
Presentation (FastAPI routes)
  → Application (use cases, schemas)
    → Service (business logic)
      → Domain (entities, value objects)
        → Infrastructure (DB, Redis, MinIO, external APIs)
```

---

## Team Contracts
| Contract | Shape |
|---|---|
| Module Interface | `async def run(job_id, tenant_id, payload) -> ModuleResult` |
| API Contract (→ Dev 2) | `GET/POST /api/v1/jobs/*`, approve/reject endpoints |
| viaSocket Payload | `{event, tenant_id, job_id, data}` — Dev 1 shapes data, I send |
| Event Names | Defined in `engine/core/events/event_types.py` (fixed enum) |

---

## Database Tables (all with UUID PK, timestamps)
| Table | Purpose |
|---|---|
| `tenants` | Multi-tenant registry |
| `tenant_secrets` | Hashed API keys (SHA-256, never plaintext) |
| `jobs` | Central work units with status machine |
| `job_logs` | Granular execution timeline per job |
| `artifacts` | Generated file metadata (MinIO stores files) |
| `webhook_events` | Inbound webhook raw payload store (store-first) |
| `viasocket_dispatches` | Outbound dispatch audit with retry history |
| `llm_usage` | Per-call token/cost tracking |
| `audit_logs` | Immutable security/action trail |
| `api_logs` | HTTP request access log |
| `notifications` | Tenant-facing dashboard notifications |
| `retry_queue` | Dead-letter store for failed async ops |

---

## Build Order (Phase Sequence)
| # | Phase | Status |
|---|---|---|
| 0 | Analysis + planning | ✅ DONE |
| 1 | Database models + Alembic + infra setup | ✅ DONE |
| 2 | Auth + Multi-tenancy service layer | ✅ DONE |
| 3 | Core FastAPI app + routes (stubs) | ✅ DONE (with Phase 2) |
| 4 | Celery queue + workers | ⬜ NEXT |
| 5 | LLM client wrapper | ⬜ PENDING |
| 6 | Webhook intake (GitHub/CI) | ⬜ PENDING |
| 7 | viaSocket dispatch | ⬜ PENDING |
| 8 | Artifact storage (MinIO) | ⬜ PENDING |
| 9 | Sandbox executor | ⬜ PENDING |
| 10 | Event system | ⬜ PENDING |
| 11 | Analytics & observability | ⬜ PENDING |
| 12 | Structured logging | ⬜ PENDING |
| 13 | Tests | ⬜ PENDING |

---

## Phase 1 — COMPLETED ✅

### Files Created
| File | Purpose |
|---|---|
| `pyproject.toml` | All dependencies, ruff, mypy, pytest config |
| `engine/config/settings.py` | Pydantic V2 Settings with sub-groups (DB/Redis/MinIO/LLM/GitHub/viaSocket/Security) |
| `engine/config/database.py` | Async SQLAlchemy engine, session factory, `get_db_session` dependency |
| `engine/core/models/base.py` | Abstract `TimestampedModel` with UUID PK, timestamps, soft-delete |
| `engine/core/models/tenant.py` | `Tenant` + `TenantSecret` (hashed API keys) |
| `engine/core/models/job.py` | `Job` + `JobLog` (state machine, Celery task ID, approval flow) |
| `engine/core/models/artifact.py` | `Artifact` (MinIO metadata, versioning, checksums) |
| `engine/core/models/webhook.py` | `WebhookEvent` (store-first, delivery_id dedup) |
| `engine/core/models/viasocket.py` | `ViaSocketDispatch` (retry history, dead-letter) |
| `engine/core/models/llm.py` | `LLMUsage` (per-call token/cost/latency tracking) |
| `engine/core/models/audit.py` | `AuditLog` + `APILog` (immutable audit trail) |
| `engine/core/models/notification.py` | `Notification` + `RetryQueue` |
| `engine/core/models/__init__.py` | All model imports for Alembic auto-discovery |
| `alembic.ini` | Alembic config with timestamped filenames |
| `infra/alembic/env.py` | Migration environment (loads settings, imports models) |
| `infra/alembic/script.py.mako` | Migration script template |
| `infra/.env.example` | All env vars with safe dev defaults |
| `infra/docker-compose.yml` | Postgres (5434), Redis (6380), MinIO (9000/9001) with healthchecks |
| `.gitignore` | Python/venv/.env/IDE exclusions |
| All `__init__.py` files | 34 package init files across full directory tree |

### Architecture Decisions (Phase 1)
- **UUIDs everywhere** — using `uuid.uuid4()` as PK, never integer auto-increment
- **JSONB for flexible data** — payload, result, raw_payload, metadata all JSONB
- **Hashed API keys** — SHA-256 stored, plaintext never persisted (shown once to user)
- **Store-first webhooks** — persist raw payload BEFORE processing, enables replay
- **Soft deletes** — `deleted_at` on base model, never physical delete of domain records
- **Composite indexes** — `jobs(tenant_id, status)`, `webhook_events(processed)` for hot query paths
- **Async engine** — asyncpg driver, separate sync URL for Alembic only
- **orjson** — faster JSON serialization for JSONB columns
- **Port offset** — Postgres on 5434, Redis on 6380 to avoid conflicts with EvalPro

---

## Phase 2 — COMPLETED ✅ (+ Phase 3 Core API bootstrapped)

### Files Created
| File | Purpose |
|---|---|
| `engine/core/auth/hasher.py` | API key generation + SHA-256 hashing + constant-time verify |
| `engine/core/auth/bearer.py` | Bearer token extraction from Authorization header |
| `engine/core/auth/__init__.py` | Auth package exports |
| `engine/core/tenants/repository.py` | Repository Pattern — ALL tenant SQL lives here |
| `engine/core/tenants/service.py` | Tenant business logic (create, auth, CRUD, key management) |
| `engine/core/tenants/__init__.py` | Tenants package exports |
| `engine/utils/exceptions.py` | Full domain exception hierarchy (AuthenticationError → JobStateError) |
| `engine/utils/logging.py` | structlog setup — JSON in prod, colorized in dev |
| `engine/api/middleware/auth.py` | Soft auth middleware (resolves tenant, never blocks public routes) |
| `engine/api/middleware/logging.py` | Request logging — request_id, latency, X-Request-ID header |
| `engine/api/dependencies/auth.py` | `get_current_tenant` FastAPI dependency (fast path + fallback) |
| `engine/api/exceptions/handlers.py` | Global exception handlers — enterprise error format, no traceback leaks |
| `engine/api/schemas/tenant.py` | Pydantic V2 schemas (CreateTenantRequest/Response, APIKeyMetadata, etc.) |
| `engine/api/routes/tenants.py` | Full tenant + API key CRUD routes |
| `engine/api/routes/health.py` | Liveness + readiness + detailed health probes |
| `engine/api/main.py` | FastAPI application factory with middleware stack + lifespan |
| `scripts/seed_demo_tenant.py` | Seed script for local testing |

### Architecture Decisions (Phase 2)
- **Two-tier auth**: Middleware does soft resolution (attaches to request.state); dependency enforces 401 on protected routes
- **Fast path auth**: Protected routes use request.state.tenant (set by middleware) — zero extra DB calls on authenticated requests
- **Constant-time key comparison**: `hmac.compare_digest` prevents timing attacks
- **Key prefix**: First 12 chars of raw key stored as `key_prefix` for user identification without exposing hash
- **Whitelist updates**: `TenantService.update_tenant` only allows specific fields — prevents mass assignment
- **Factory pattern**: `create_application()` factory enables isolated test instances
- **Middleware order**: CORS → RequestLogging → Auth (outermost to innermost)
- **Soft auth middleware**: Webhooks bypass auth (they use their own signature verification)

---

## Phase 4 — NEXT: Celery Queue + Workers
**Will create**:
- `engine/core/queue/celery_app.py` — Celery app with Redis broker
- `engine/core/queue/task_router.py` — Task routing by module type
- `engine/workers/execute_module.py` — Main Celery task (idempotent, with retry/backoff)
- `engine/workers/retry_handler.py` — Dead-letter queue handler
- `engine/workers/health.py` — Worker health reporting
- `engine/api/schemas/job.py` — Job request/response Pydantic schemas
- `engine/api/routes/jobs.py` — Job CRUD + approve/reject endpoints
- `engine/core/jobs/repository.py` — Job repository
- `engine/core/jobs/service.py` — Job orchestration service

---

## Prompt Log / History
| # | Prompt Summary | Status |
|---|---|---|
| 1 | Initialize GitHub repo + push markdown files | ✅ Done |
| 2 | Analyze handover docs + create memory.md | ✅ Done |
| 3 | Full architecture setup — divide into phases, start with Phase 1 DB | ✅ Done |
| 4 | Continue → Phase 2 Auth + Multi-Tenancy + FastAPI bootstrap | ✅ Done |

---

## Known Issues / Gotchas
- Docker Postgres uses port 5434 (not 5432) to avoid EvalPro conflict — update `.env` accordingly
- Alembic uses psycopg2 sync URL — `asyncpg` URL must NOT be used in `env.py`
- `psycopg2` must be installed for Alembic sync engine (`pip install psycopg2-binary`)
- Run `alembic upgrade head` before starting the API server
- `structlog` must be installed for logging to work (`pip install structlog`)

---

*Always read this file first. Update after every completed phase or prompt.*
