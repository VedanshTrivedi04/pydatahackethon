# SKILL.md — ShipFaster Platform

This file is the shared source of truth for all 3 developers. Read this before touching any module. It defines architecture boundaries, conventions, and contracts so nobody breaks another dev's part.

## Project summary

ShipFaster is a unified developer-automation platform with 5 modules (scaffolder, test generator, docs generator, changelog generator, notebook-to-blog) exposed via CLI + MCP server, orchestrated through a shared core engine, and connected back into GitHub/Slack/LinkedIn via viaSocket webhooks.

## Team split

| Owner | Scope | Primary dirs |
|---|---|---|
| Dev 1 — Agent & Automation | LLM orchestration, all 5 module logic, MCP server, prompt engineering, viaSocket payload construction | `/engine/modules/`, `/engine/mcp/`, `/engine/prompts/` |
| Dev 2 — Frontend | Dashboard UI, job history, approve/reject flow, docs preview, landing page | `/frontend/` |
| Dev 3 — Backend/DB/Integration (you) | Core API, DB schema, auth, multi-tenancy, Celery/Redis queue, webhook receivers, viaSocket dispatch, CI/CD | `/engine/core/`, `/engine/api/`, `/infra/` |

**Rule**: nobody edits outside their primary dir without a heads-up in the team channel. Shared contracts (below) are the only touchpoints.

## Architecture (recap)

```
CLI / git webhook / MCP call
        ↓
Core engine (FastAPI) — auth, tenant resolution, job dispatch   [Dev 3]
        ↓
Module router → 5 modules (scaffolder, test-gen, docs-gen, changelog, notebook-to-blog)  [Dev 1]
        ↓
Celery worker (Redis queue) — async LLM execution, retries    [Dev 3]
        ↓
PostgreSQL (job state, artifacts metadata) + S3 (artifact files)   [Dev 3]
        ↓
viaSocket webhook dispatch → GitHub Release / Slack / LinkedIn   [Dev 3, payload built by Dev 1]
        ↑
Frontend dashboard (job history, approve/reject, docs preview)   [Dev 2]
```

## Contracts between roles (do not break these without team sign-off)

### 1. Module interface (Dev 1 → Dev 3)
Every module exposes one async function with this exact signature:

```python
async def run(job_id: str, tenant_id: str, payload: dict) -> ModuleResult:
    """
    payload: module-specific input (e.g. {"repo_url": ..., "commit_range": ...})
    returns ModuleResult(status: Literal["success","failed","partial"],
                          output: dict, artifacts: list[str], error: str | None)
    """
```
Dev 3's Celery worker calls `run()` — it never inspects module internals. Dev 1 never touches Celery/queue code.

### 2. Job status API (Dev 3 → Dev 2)
```
GET  /api/v1/jobs/{job_id}          -> { status, module, created_at, result }
GET  /api/v1/jobs?tenant_id=&module= -> paginated list
POST /api/v1/jobs/{job_id}/approve  -> triggers viaSocket publish (notebook-to-blog only)
POST /api/v1/jobs/{job_id}/reject
```
Dev 2 builds UI strictly against this contract. Any new field request goes through Dev 3.

### 3. viaSocket payload contract (Dev 1 builds it, Dev 3 sends it)
```json
{
  "event": "changelog.generated",
  "tenant_id": "...",
  "job_id": "...",
  "data": { "release_notes_md": "...", "version": "...", "repo": "..." }
}
```
Dev 1 owns the `data` shape per event type. Dev 3 owns delivery (retry, signing, logging). Event names are fixed enum — see `/engine/core/events.py`.

## Coding conventions

- Python 3.12, `ruff` for lint/format, `mypy` strict on `/engine/core` and `/engine/api`
- All DB access through SQLAlchemy async models — no raw SQL in module code
- Every LLM call goes through `engine.core.llm_client` (Dev 3's wrapper) — never call Anthropic SDK directly from modules, so token usage/cost tracking stays centralized
- Commit convention: `feat(module):`, `fix(api):`, `chore(infra):` — this literally feeds the changelog generator, so be disciplined
- Branch naming: `dev1/`, `dev2/`, `dev3/` prefixes to avoid PR confusion

## Environment

- `.env` template in `/infra/.env.example` — copy to `.env`, never commit real keys
- Local stack: `docker-compose up` brings up Postgres + Redis + MinIO (S3-compatible) — see SUPERPOWER.md for commands

## Non-negotiables (enterprise-level bar)

- Every generated artifact (test file, docs, changelog) is tenant-scoped — no cross-tenant leakage, ever
- Every webhook receiver verifies signature before processing
- Every Celery task is idempotent — re-running a job with the same `job_id` must not duplicate side effects
- No secrets in logs, ever — Dev 3 enforces this in the logging middleware
