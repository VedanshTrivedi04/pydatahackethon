# ShipFaster Dev 3 (Backend) — Memory & Context

_Last Updated: All Phases Complete_

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
| 7 | viaSocket dispatch | ✅ DONE |
| 8 | Artifact storage (MinIO) | ✅ DONE |
| 9 | Sandbox executor | ✅ DONE |
| 10 | Event system | ✅ DONE |
| 11 | Analytics & observability | ✅ DONE |
| 12 | Structured logging | ✅ DONE (Built in Phase 0) |
| 13 | Tests | ✅ DONE |

---
## 🎉 BACKEND ARCHITECTURE FULLY COMPLETE 🎉

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

## Phase 7 — COMPLETED ✅ (viaSocket Dispatch)

### Files Created
| File | Purpose |
|---|---|
| `engine/core/viasocket/contracts.py` | Strict outbound Pydantic schema (`ViaSocketPayload`) |
| `engine/core/viasocket/client.py` | Synchronous HTTP client (`urllib.request`) for Celery worker |
| `engine/core/viasocket/service.py` | DB persistence for `ViaSocketDispatch` audit log with retry states |
| `engine/workers/viasocket_dispatcher.py` | Dedicated low-priority Celery task for async dispatching |
| `engine/core/viasocket/__init__.py` | Package exports |

### Integration Points
- **`execute_module.py`**: Automatically enqueues the dispatch task if a module succeeds and doesn't require approval.
- **`engine/core/jobs/service.py`**: `_trigger_post_approval_dispatch` enqueues the dispatch task instantly when a user hits `/approve`.

### Architecture Decisions (Phase 7)
- **Async Execution**: The HTTP POST never blocks the main AI worker (`execute_module.py`); it fires a separate Celery task.
- **Built-in Retries**: Leverages Celery's exponential backoff (`task.retry`) instead of implementing a custom polling loop.
- **Full DB Audit**: `viasocket_dispatches` table tracks the raw payload, URL, HTTP status code, and `attempt_count` for perfect observability.

---

## Phase 8 — COMPLETED ✅ (Artifact Storage / MinIO)

### Files Created
| File | Purpose |
|---|---|
| `engine/core/storage/client.py` | Wrapper for `boto3` to communicate with MinIO (uploads and presigned URLs). |
| `engine/core/artifacts/repository.py` | Stores artifact metadata, handles versioning for identical filenames. |
| `engine/core/artifacts/service.py` | Coordinates uploading to storage and creating the DB record, calculates checksums. |
| `engine/api/routes/artifacts.py` | `GET /api/v1/artifacts/{id}/download` route that returns short-lived presigned URLs. |
| `engine/core/queue/contracts.py` | Updated `ModuleResult` and created `ArtifactData` so modules can return raw file content natively. |

### Integration Points
- **`execute_module.py`**: Now extracts raw files from the module result, uploads them to MinIO via `ArtifactService`, and prevents giant binary strings from being saved to the PostgreSQL JSONB `jobs` output field.

### Architecture Decisions (Phase 8)
- **Boto3 vs Minio SDK**: Used `boto3` because it's the universal standard for S3-compatible APIs.
- **Short-Lived URLs**: Instead of streaming files through FastAPI (which blocks async workers), we generate presigned URLs directly to MinIO.
- **Clean JSONB**: The job's JSONB output now only contains a summary of artifacts (`_artifacts: [{"file_name": ...}]`), not the binary data.

---

## Phase 9 — COMPLETED ✅ (Sandbox Executor)

### Files Created
| File | Purpose |
|---|---|
| `engine/config/settings.py` | Added `SandboxSettings` (`sandbox.endpoint_url`, `sandbox.api_key`). |
| `engine/core/sandbox/client.py` | Built `SandboxClient` using `urllib.request` to hit the execution API. |
| `engine/core/sandbox/__init__.py` | Package exports. |
| `engine/core/queue/contracts.py` | Updated `ModuleResult` with `sandbox_logs` field. |

### Integration Points
- **`execute_module.py`**: Intercepts `sandbox_logs` from the `ModuleResult` and injects them into the safe JSON output, allowing the frontend to display execution logs (e.g. pytest output from `test_generator`).

### Architecture Decisions (Phase 9)
- **External Execution**: To ensure absolute security and prevent malicious code from destroying the host, we rely on an external execution API rather than running Docker locally within the Python process.
- **Log Preservation**: We don't discard the logs. Storing `_sandbox_logs` directly inside the job output means developers can easily view the execution trace of the code the AI generated.

---

## Phase 10 — COMPLETED ✅ (Event System)

### Files Created
| File | Purpose |
|---|---|
| `engine/core/events/types.py` | Defined standard `SystemEvent` Pydantic schema and allowed `EventType`s. |
| `engine/core/events/bus.py` | Built a lightweight async in-memory Pub/Sub `EventBus` singleton. |
| `engine/core/events/__init__.py` | Package exports. |

### Integration Points
- **`JobService`**: Emits `job.created`, `job.status_changed`, `job.completed`, and `job.failed` internally so other modules (like a future notifications engine) can hook into the job lifecycle without adding spaghetti logic to `JobService`.

### Architecture Decisions (Phase 10)
- **Decoupling**: The system can now add new reactions to standard state changes just by calling `event_bus.subscribe()`.

---

## Phase 11 — COMPLETED ✅ (Analytics & Observability)

### Files Created
| File | Purpose |
|---|---|
| `engine/api/schemas/analytics.py` | Pydantic response models for Job and LLM usage summaries. |
| `engine/api/routes/analytics.py` | `GET /api/v1/analytics/jobs/summary` and `GET /api/v1/analytics/llm/usage`. |

### Integration Points
- Re-used `JobRepository.count_by_status` and `LLMUsageTracker.get_usage_summary` (built in Phase 5) to serve real-time metrics back to the frontend without heavy new queries.

### Architecture Decisions (Phase 11)
- **Aggregation Strategy**: Kept aggregates calculated dynamically at request time (via SQL `COUNT` and `SUM`). If the data grows massive, we would move this to materialized views, but this simple DB approach is perfect for early enterprise scale.

---

## Phase 12 — COMPLETED ✅ (Structured Logging)

*Note: This was proactively implemented during Phase 0 (Infrastructure Setup).*

### Files Created
| File | Purpose |
|---|---|
| `engine/utils/logging.py` | Complete `structlog` configuration. |

### Architecture Decisions (Phase 12)
- **JSON for Production**: Automatically switches to JSON formatting (`structlog.processors.JSONRenderer()`) when `environment != development`. This means the logs are already perfectly formatted for Datadog or ELK.
- **Context Vars**: The `bind_request_context` method injects `request_id`, `tenant_id`, and `job_id` into the thread-local context so *every* log line automatically includes them without devs needing to pass them manually.

---

## Phase 13 — COMPLETED ✅ (Tests)

### Files Created
| File | Purpose |
|---|---|
| `tests/conftest.py` | Pytest setup and mock DB session / repository fixtures. |
| `tests/test_jobs_service.py` | Unit tests for `JobService` ensuring jobs are queued, Celery tasks dispatched, and `event_bus` events emitted. |
| `tests/test_llm_usage.py` | Unit tests for `LLMUsageTracker` ensuring aggregation queries execute correctly. |

### Architecture Decisions (Phase 13)
- **Dependency Injection**: Because we aggressively used Clean Architecture patterns (passing `session` and `repository` into our service layers), unit testing was extremely easy. We didn't need to spin up a real Postgres database just to test if a job fires an event.
- **AsyncMock**: Leveraged `unittest.mock.AsyncMock` to cleanly test our async core without complex event loop setups.

---

## 🚀 ROADMAP COMPLETE 🚀
The initial ShipFaster backend architecture is completely built out and ready for product-level feature development!

---

## Architecture Audit & Enterprise Gap Analysis (Post-Phase 13)

A comprehensive architectural review of the codebase identified that while the Clean Architecture foundation is solid, several critical SaaS capabilities are missing for a true production release.

**Key Missing Features:**
1. **Distributed Event Bus (Redis Streams/PubSub)**: The current `EventBus` is purely in-memory. Celery events do not reach the FastAPI server.
2. **Distributed Tracing**: `request_id` drops at the Celery boundary. No correlation IDs.
3. **API Rate Limiting**: The system is vulnerable to LLM cost abuse without per-tenant token bucket limiters.
4. **Identity & RBAC**: The system uses machine API keys but lacks Human Users, Roles, and JWT Auth.
5. **Observability**: Missing OpenTelemetry and `/metrics` for Prometheus.
6. **Feature Flags**: Missing tier-based access toggles (e.g., Notebook disabled for Free tier).
7. **Subscription Plans**: Missing Free/Pro/Enterprise plans with token and storage limits.
8. **Billing Layer**: Missing integration hooks for Stripe/future billing engines.
9. **Secret Manager**: `tenant_secrets` lacks rotation, versioning, and expiry capabilities.
10. **API Gateway Readiness**: Missing forwarded headers, trusted proxy config, and rate limit headers.
11. **Background Scheduler**: Celery is installed, but Celery Beat / APScheduler is missing for cron jobs (e.g., nightly backups, syncing limits).
12. **Cache Layer**: Missing Redis caching for heavy queries (Analytics, LLM Pricing).
13. **Search Engine**: Missing Job/Artifact/Webhook search (Elasticsearch / Postgres FTS).
14. **Disaster Recovery & Backup Strategy**: Missing nightly DB to S3 backups and graceful fallback when Redis/MinIO goes down.
15. **Contract Testing**: Missing API OpenAPI validation (Dev2) and `ModuleResult` strict validation (Dev1) to ensure integration day has zero surprises.

---

## Future Roadmap: Enterprise Readiness (Phases 13.5 - 30)

| # | Phase | Status |
|---|---|---|
| 13.5 | Foundation Hardening | ✅ DONE |
| 14 | Correlation IDs | ✅ DONE |
| 15 | Redis Streams Event Bus | ✅ DONE |
| 16 | Rate Limiter | ✅ DONE |
| 17 | RBAC | ⬜ NEXT |
| 18 | Observability | ⬜ PENDING |
| 19 | Feature Flags | ⬜ PENDING |
| 20 | Subscription Plans | ⬜ PENDING |
| 21 | Cache Layer | ⬜ PENDING |
| 22 | Scheduler | ⬜ PENDING |
| 23 | Production Hardening | ⬜ PENDING |
| 24 | CI/CD | ⬜ PENDING |
| 25 | Backup | ⬜ PENDING |
| 26 | Disaster Recovery | ⬜ PENDING |
| 27 | Contract Testing | ⬜ PENDING |
| 28 | Performance Benchmark | ⬜ PENDING |
| 29 | Security Audit | ⬜ PENDING |
| 30 | Production Release | ⬜ PENDING |

---

## Phase 14 — COMPLETED ✅ (Distributed Tracing & Correlation)

### Files Modified
| File | Purpose |
|---|---|
| `engine/utils/logging.py` | Added `correlation_id` to `bind_request_context` to attach to `structlog`. |
| `engine/api/middleware/logging.py` | Extracted `X-Correlation-ID` (or generated it) and passed it to `bind_request_context`. |
| `engine/core/jobs/service.py` | Extracted the `correlation_id` from structlog context and injected it into `celery_app.send_task(headers={"x-correlation-id": ...})`. |
| `engine/core/queue/celery_app.py` | Intercepted Celery's `task_prerun` signal to extract the header and bind it to structlog context in the worker, then cleared it in `task_postrun`. |

### Architecture Decisions (Phase 14)
- **100% Trace Visibility**: Every single log line emitted from FastAPI *and* Celery for a specific API request will now share the exact same `correlation_id`, making debugging distributed AI workflows seamless in Datadog/ELK.

---

## Phase 15 — COMPLETED ✅ (Distributed Event Bus - Redis)

### Files Modified
| File | Purpose |
|---|---|
| `engine/core/events/bus.py` | Completely rewrote `EventBus` to connect to Redis, publish events to `shipfaster.events`, and run an `asyncio` listener loop to trigger local subscribers. |
| `engine/api/main.py` | Updated application `lifespan` to `await event_bus.connect()` on startup and `disconnect()` on shutdown. |

### Architecture Decisions (Phase 15)
- **Redis Pub/Sub**: Replaced the isolated in-memory event bus. Now, when a Celery worker completes a job, the event is serialized to JSON and broadcasted across Redis. Every connected FastAPI instance will receive the event instantly, allowing them to push real-time WebSocket updates to the frontend dashboard.
- **Test Fallback**: If Redis isn't connected, the bus silently degrades back to an in-memory loop so unit tests don't break.

---

## Phase 16 — COMPLETED ✅ (API Rate Limiting)

### Files Modified
| File | Purpose |
|---|---|
| `engine/api/middleware/rate_limiter.py` | Built `RateLimiterMiddleware` using Redis pipelines and a Fixed Window algorithm. |
| `engine/api/main.py` | Registered the middleware immediately after `AuthMiddleware`. |

### Architecture Decisions (Phase 16)
- **Granular Limits**: Separated limits for authenticated traffic (per `tenant_id`) and unauthenticated traffic (per `X-Forwarded-For` IP address).
- **Graceful Degradation**: If Redis fails or goes offline, the `RateLimiterMiddleware` fails open (catches the exception and calls `call_next`). It will not bring down the entire API just because caching went down.
- **Standardized Headers**: Returns 429 Too Many Requests with standard `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.

---

## Phase 17 — NEXT: Identity, Users & RBAC
**Will create**:
- `users` and `tenant_members` tables.
- Role-based access control (Admin, Developer, Viewer).
- JWT Authentication flow (`engine/api/routes/auth.py`).

---

## Phase 14 — PROPOSED: Distributed Tracing & Correlation
**Will create**:
- Inject `X-Correlation-ID` into Celery task headers.
- Extract headers in worker signals to bind to `structlog` context, achieving 100% trace visibility across API and Workers.

---

## Phase 15 — PROPOSED: Distributed Event Bus (Redis)
**Will create**:
- Upgrade `engine/core/events/bus.py` to use `redis.asyncio` for Pub/Sub.
- Enables Fast API to subscribe to Redis channels for WebSocket broadcast.

---

## Phase 16 — PROPOSED: API Rate Limiting
**Will create**:
- Redis sliding window rate limiter middleware (`engine/api/middleware/rate_limiter.py`).
- Protect infrastructure and LLM budgets based on tenant tiers.

---

## Phase 17 — PROPOSED: Identity, Users & RBAC
**Will create**:
- `users` and `tenant_members` tables.
- Role-based access control (Admin, Developer, Viewer).
- JWT Authentication flow (`engine/api/routes/auth.py`).

---

## Phase 18 — PROPOSED: OpenTelemetry & Metrics
**Will create**:
- `/metrics` endpoint for Prometheus scraping.
- Instrument FastAPI and Celery with `opentelemetry-python`.

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
| 8   | Continue → Phase 7 viaSocket Dispatch                               | ✅ Done |
| 9   | Continue → Phase 8 Artifact Storage (MinIO)                         | ✅ Done |
| 10  | Continue → Phase 9 Sandbox Executor                                 | ✅ Done |
| 11  | Continue → Phase 10 Event System                                    | ✅ Done |
| 12  | Continue → Phase 11 Analytics & Observability                       | ✅ Done |
| 13  | Continue → Phase 12 Structured Logging                              | ✅ Done |
| 14  | Continue → Phase 13 Tests                                           | ✅ Done |
| 15  | Stop and perform complete architectural review + plan new phases    | ✅ Done |
| 16  | Identify missing features (Feature flags, RBAC, etc.) + Update Roadmap | ✅ Done |
| 17  | Continue → Phase 14 Correlation IDs                                 | ✅ Done |
| 18  | Continue → Phase 15 Redis Event Bus                                 | ✅ Done |
| 19  | Continue → Phase 16 Rate Limiter                                    | ✅ Done |

---

## Known Issues / Gotchas
- Docker Postgres uses port 5434 (not 5432) to avoid EvalPro conflict — update `.env` accordingly
- Alembic uses psycopg2 sync URL — `asyncpg` URL must NOT be used in `env.py`
- `psycopg2` must be installed for Alembic sync engine (`pip install psycopg2-binary`)
- Run `alembic upgrade head` before starting the API server
- `structlog` must be installed for logging to work (`pip install structlog`)

---

*Always read this file first. Update after every completed phase or prompt.*
