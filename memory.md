# ShipFaster Dev 3 (Backend) — Memory & Context

_Last Updated: Phase 6 Complete_

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
| 4 | Celery queue + workers | ✅ DONE |
| 5 | LLM client wrapper (Gemini-only) | ✅ DONE |
| 6 | Webhook intake (GitHub/CI) | ✅ DONE |
| 7 | viaSocket dispatch | ⬜ NEXT |
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

## Phase 4 — COMPLETED ✅

### Files Created
| File | Purpose |
|---|---|
| `engine/core/queue/celery_app.py` | Celery app — 4 queues (high/default/low/dlq), task routing, signal handlers |
| `engine/core/queue/contracts.py` | `ModuleResult` — Dev1→Dev3 contract schema |
| `engine/core/queue/__init__.py` | Queue package exports |
| `engine/core/jobs/repository.py` | Job Repository Pattern — all SQL, paginated listing, approval flow, analytics |
| `engine/core/jobs/service.py` | Job Service — submit (create+enqueue), lifecycle, approval, worker callbacks |
| `engine/core/jobs/__init__.py` | Jobs package exports |
| `engine/workers/execute_module.py` | Main Celery task — idempotency, dynamic module import, exponential backoff, DLQ |
| `engine/workers/retry_handler.py` | DLQ handler — creates RetryQueue record + Notification on permanent failure |
| `engine/workers/health.py` | Worker health check via control.inspect() |
| `engine/api/schemas/job.py` | Pydantic V2 schemas — all job request/response models |
| `engine/api/routes/jobs.py` | 8 job routes — submit, list, detail, status poll, logs, approve, reject, stats |
| `engine/api/main.py` | Updated — jobs router registered |
| `Makefile` | Developer convenience: make up/api/worker/migrate/seed/test |

### Architecture Decisions (Phase 4)
- **4 named queues**: high (scaffolder/test_gen) / default (docs/changelog) / low (notebook_to_blog) / dlq
- **Module-to-queue routing**: `MODULE_QUEUE_MAP` in celery_app.py — each module goes to appropriate queue
- **Idempotency**: Worker checks `job.status == success` before executing — safe against duplicate deliveries
- **Dynamic import**: `MODULE_HANDLER_MAP` — if Dev 1's module doesn't exist yet, job fails gracefully (not worker crash)
- **Exponential backoff**: 60s → 120s between retries (2 retries = 3 total attempts)
- **DLQ routing**: After all retries, job sent to `shipfaster.dlq` + RetryQueue record + Notification created
- **asyncio.run() bridge**: Celery is sync; modules are async. Bridge via `asyncio.run()` inside the task
- **acks_late + reject_on_worker_lost**: At-least-once delivery with crash safety
- **202 Accepted**: Job submit returns immediately, not 201 Created (job is async)
- **Lightweight status poll**: Separate `GET /jobs/{id}/status` for polling without loading logs

---

## Phase 5 — COMPLETED ✅ (Gemini-Only Architecture)

### Files Created
| File | Purpose |
|---|---|
| `engine/core/llm/client.py` | Single entry point for `LLMClient` — uses `google.genai` SDK |
| `engine/core/llm/types.py` | Value objects: `LLMCallResult`, `LLMGenerationConfig` |
| `engine/core/llm/pricing.py` | Cost tables for Gemini 2.5 Flash, 2.5 Pro, 2.0 Flash, 1.5 Flash |
| `engine/core/llm/usage_tracker.py` | `LLMUsageTracker` for cost analytics and cap enforcement |
| `engine/core/llm/__init__.py` | Easy exports for Dev 1 |
| `engine/config/settings.py` | Updated `LLMSettings` to explicitly use `gemini_api_key` |

### Architecture Decisions (Phase 5)
- **Gemini Only**: Dropped Claude fallback to simplify the architecture. Primary model is `gemini-2.5-flash`.
- **Async Native**: Uses the new `client.aio.models.generate_content`.
- **Tenacity Retries**: Exponential backoff (2-30s) + jitter on 429s and 5xxs. No retries on 400s.
- **Cost Calculation**: Centralized cost calculation (input, output, and thinking tokens).
- **Auto-Persistence**: Passing `session` to `generate()` automatically writes to `llm_usage`.
- **Thinking Budget**: Full support for configuring Gemini 2.5 thinking budgets.
- **Structured Output**: `generate_json()` forces `application/json` response MIME type.

---

## Phase 6 — COMPLETED ✅ (Webhook Intake)

### Files Created
| File | Purpose |
|---|---|
| `engine/api/schemas/webhook.py` | Payload definitions (e.g., extracting GitHub installation ID) |
| `engine/core/webhooks/security.py` | HMAC SHA-256 signature validation matching GitHub's algorithm |
| `engine/core/webhooks/repository.py` | `WebhookRepository` with store-first and deduplication logic |
| `engine/core/webhooks/service.py` | Resolves tenant by `installation_id`, persists event, creates `Job` |
| `engine/core/webhooks/__init__.py` | Package exports |
| `engine/api/routes/webhooks.py` | `POST /api/v1/webhooks/github` — no auth, relies on HMAC signature |
| `engine/api/main.py` | Registered webhook router |

### Architecture Decisions (Phase 6)
- **Store-First Pattern**: `WebhookEvent` raw JSON is persisted BEFORE any business logic runs (for audit/replay).
- **Idempotency**: Checked against `X-GitHub-Delivery` ID via DB constraint / query.
- **Tenant Resolution**: Instead of an API key, tenants are identified by mapping the webhook's `installation.id` to `Tenant.github_app_installation_id`.
- **Automatic Job Enqueueing**: Built basic event-to-module mapping (e.g., `pull_request` -> `test_generator`) that automatically enqueues a Celery job.

---

## Phase 7 — NEXT: viaSocket Dispatch
**Will create**:
- `engine/core/viasocket/contracts.py` — Schema for the outbound payload (`{event, tenant_id, job_id, data}`).
- `engine/core/viasocket/client.py` — Resilient HTTP client (with retry/timeout).
- `engine/workers/viasocket_dispatcher.py` — Async Celery task to send webhooks without blocking main queue.
- `engine/core/viasocket/service.py` — Orchestrates tracking in `ViaSocketDispatch` DB model.
- **Integration**: Update `execute_module.py` (from Phase 4) to trigger this task on job success.

---

## Prompt Log / History
| #   | Prompt Summary                                                      | Status |
| -----| ---------------------------------------------------------------------| --------|
| 1   | Initialize GitHub repo + push markdown files                        | ✅ Done |
| 2   | Analyze handover docs + create memory.md                            | ✅ Done |
| 3   | Full architecture setup — divide into phases, start with Phase 1 DB | ✅ Done |
| 4   | Continue → Phase 2 Auth + Multi-Tenancy + FastAPI bootstrap         | ✅ Done |
| 5   | Continue → Phase 4 Celery Queue + Workers + Job API                 | ✅ Done |
| 6   | Continue → Phase 5 LLM Client Wrapper (Gemini-only)                 | ✅ Done |
| 7   | Continue → Phase 6 Webhook Intake (GitHub/CI)                       | ✅ Done |

---

## Known Issues / Gotchas
- Docker Postgres uses port 5434 (not 5432) to avoid EvalPro conflict — update `.env` accordingly
- Alembic uses psycopg2 sync URL — `asyncpg` URL must NOT be used in `env.py`
- `psycopg2` must be installed for Alembic sync engine (`pip install psycopg2-binary`)
- Run `alembic upgrade head` before starting the API server
- `structlog` must be installed for logging to work (`pip install structlog`)

---

*Always read this file first. Update after every completed phase or prompt.*
