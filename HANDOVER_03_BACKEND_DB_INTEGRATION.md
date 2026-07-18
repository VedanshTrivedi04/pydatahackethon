# Handover — Backend / DB / Integration Developer (Dev 3 — you)

Read SKILL.md first for shared contracts. This file is your scope — the biggest one, since it's the glue holding Dev 1 and Dev 2's work together.

## Your mission

Core API, database schema, multi-tenancy, auth, the job queue, webhook intake, and the viaSocket dispatch layer. Everything the other two devs build ON TOP OF.

## Your directories

```
engine/
  core/
    models.py           # all SQLAlchemy models
    events.py            # fixed event enum
    llm_client.py         # centralized Claude API wrapper
    celery_app.py
    sandbox.py            # isolated code execution for test-gen validation
    storage.py             # S3/artifact save + fetch
  api/
    main.py
    routes/
      jobs.py
      tenants.py
      auth.py
infra/
  webhook_receiver.py     # GitHub/CI intake
  viasocket_dispatch.py
  docker-compose.yml
  alembic/                # migrations
```

## Database schema (build this first — everything depends on it)

```sql
tenants
  id UUID PK
  name TEXT
  api_key_hash TEXT
  github_app_installation_id TEXT
  viasocket_webhook_url TEXT
  created_at TIMESTAMPTZ

jobs
  id UUID PK
  tenant_id UUID FK -> tenants
  module TEXT  -- 'scaffolder' | 'test_generator' | 'docs_generator' | 'changelog_generator' | 'notebook_to_blog'
  status TEXT  -- 'queued' | 'running' | 'success' | 'failed' | 'partial'
  payload JSONB
  result JSONB
  error TEXT
  created_at TIMESTAMPTZ
  completed_at TIMESTAMPTZ

artifacts
  id UUID PK
  job_id UUID FK -> jobs
  file_name TEXT
  s3_key TEXT
  content_type TEXT

webhook_events
  id UUID PK
  tenant_id UUID FK -> tenants
  source TEXT  -- 'github' | 'ci'
  event_type TEXT
  raw_payload JSONB
  processed BOOLEAN DEFAULT false
  received_at TIMESTAMPTZ

viasocket_dispatches
  id UUID PK
  job_id UUID FK -> jobs
  event_name TEXT
  payload_sent JSONB
  status_code INT
  attempt_count INT
  dispatched_at TIMESTAMPTZ

llm_usage
  id UUID PK
  tenant_id UUID FK -> tenants
  job_id UUID FK -> jobs
  model TEXT
  input_tokens INT
  output_tokens INT
  created_at TIMESTAMPTZ
```

Index `jobs(tenant_id, status)` and `webhook_events(processed)` — you'll query these constantly.

## Core engine responsibilities

### 1. Auth + tenant resolution
- API key in `Authorization: Bearer` header → hash, look up `tenants` table → attach `tenant_id` to request context
- Every downstream query filters by `tenant_id` — no exceptions, this is your security boundary

### 2. `llm_client.complete()`
Centralized wrapper Dev 1's modules call instead of the raw SDK:
```python
async def complete(tenant_id: str, job_id: str, system: str, messages: list, model="claude-sonnet-4-6") -> str:
    # call Anthropic API, log to llm_usage table, handle retries/timeouts
```
This is where you get cost visibility per tenant — non-negotiable for the "enterprise" pitch.

### 3. Celery task wrapper
```python
@celery_app.task(bind=True, max_retries=2)
def execute_module(self, job_id, tenant_id, module_name, payload):
    # look up module handler by module_name, call run(), persist ModuleResult to jobs table
    # on failure, retry with backoff; on final failure, status='failed'
```
Idempotency: check `jobs.status` before executing — if already `success`, skip (protects against duplicate Celery deliveries).

### 4. Sandbox for test validation
Dev 1 needs `engine.core.sandbox.execute(code: str) -> (passed: bool, output: str)`. Simplest safe approach for a hackathon: spin up a subprocess with a timeout, in a throwaway venv or a lightweight Docker container (`docker run --rm --network=none python:3.12-slim`). No network access for the sandboxed process — this matters if a judge asks about security.

### 5. Webhook intake (`infra/webhook_receiver.py`)
- `POST /webhooks/github` — verify `X-Hub-Signature-256` against tenant's GitHub app secret before touching payload
- On `push`/`release` events → create a `changelog_generator` + `docs_generator` job, dispatch to Celery
- On CI failure events → create a job for root-cause analysis (Dev 1 builds the module, you just wire the trigger)
- Store raw payload in `webhook_events` regardless — audit trail

### 6. viaSocket dispatch (`infra/viasocket_dispatch.py`)
```python
async def dispatch(tenant_id: str, job_id: str, event_name: str, data: dict):
    url = get_tenant_viasocket_url(tenant_id)
    payload = {"event": event_name, "tenant_id": tenant_id, "job_id": job_id, "data": data}
    # POST with retry (3 attempts, exponential backoff), log to viasocket_dispatches
```
Called automatically when a job reaches `success` for changelog/docs/CI-analysis modules. For notebook-to-blog, only called after the `/jobs/{id}/approve` endpoint is hit (human gate — Dev 2's UI triggers this).

## API endpoints you own (Dev 2 depends on these)

```
GET  /api/v1/jobs
GET  /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/approve
POST /api/v1/jobs/{job_id}/reject
GET  /api/v1/jobs/{job_id}/artifacts/{artifact_id}
POST /webhooks/github
POST /webhooks/ci
```
Publish an OpenAPI schema early (`GET /openapi.json` is free with FastAPI) so Dev 2 can generate a typed client immediately — don't make them wait for your endpoints to be "done," give them the schema on day 1 even with stub responses.

## Build order (your personal sequence)

1. DB schema + migrations (Alembic) — do this first, both other devs are blocked without it conceptually
2. `tenants` + auth middleware
3. Stub job endpoints returning fake data (unblocks Dev 2 immediately)
4. Celery + Redis wiring, `execute_module` task
5. `llm_client` wrapper (Dev 1 needs this to start real module work)
6. Webhook receiver + signature verification
7. viaSocket dispatch + retry logic
8. Sandbox executor (needed once Dev 1's test-gen module is ready to validate)
9. Wire it all end-to-end, test the full loop: GitHub push → job → viaSocket → Slack

## What NOT to do

- Don't write module logic yourself — that's Dev 1's job, you only call `run()`
- Don't let Dev 2 query the DB directly, ever — API only, even for convenience during the hackathon
- Don't skip signature verification on webhooks "just for the demo" — an unverified webhook receiver is the single easiest thing for a judge to poke a hole in
