# SUPERPOWER.md — ShipFaster Quick Reference

Fast-lookup cheat sheet. Full context lives in SKILL.md and your role's handover file. This is for "I forgot the command" moments.

## Local setup (all devs)

```bash
git clone <repo>
cd shipfaster
cp infra/.env.example .env          # fill in ANTHROPIC_API_KEY, VIASOCKET_WEBHOOK_URL, GITHUB_APP creds
docker-compose up -d                # Postgres:5432, Redis:6379, MinIO:9000
pip install -e ".[dev]" --break-system-packages
alembic upgrade head                # apply DB migrations
```

## Running things

| What | Command |
|---|---|
| Core API (Dev 3) | `uvicorn engine.api.main:app --reload --port 8000` |
| Celery worker (Dev 3) | `celery -A engine.core.celery_app worker --loglevel=info` |
| Frontend dev server (Dev 2) | `cd frontend && npm run dev` |
| MCP server standalone (Dev 1) | `python -m engine.mcp.server` |
| CLI local test | `python -m engine.cli init --stack fastapi` |
| Run all tests | `pytest -v` |
| Generate a test migration | `alembic revision --autogenerate -m "message"` |

## Key files map

| File | Owns |
|---|---|
| `engine/core/models.py` | All SQLAlchemy models — tenants, jobs, artifacts, events |
| `engine/core/events.py` | Fixed enum of viaSocket event names — don't add without team sync |
| `engine/core/llm_client.py` | Central Claude API wrapper — cost tracking, retries live here |
| `engine/core/celery_app.py` | Queue config, task registration |
| `engine/api/routes/jobs.py` | Job status/approve/reject endpoints — Dev 2's main contract |
| `engine/modules/*/handler.py` | One folder per module, each with `run()` — Dev 1's territory |
| `engine/mcp/server.py` | MCP tool registration wrapping the 5 modules |
| `frontend/src/api/client.ts` | Typed API client generated from OpenAPI schema |
| `infra/webhook_receiver.py` | GitHub/CI webhook intake, signature verification |
| `infra/viasocket_dispatch.py` | Outbound POST to viaSocket, retry/backoff logic |

## Common gotchas

- **"My module isn't showing in job history"** → check `ModuleResult.status` is one of the exact 3 literals, Dev 3's serializer rejects anything else silently in dev mode (fixed in prod, but fix your enum now)
- **"LLM call failing with 401"** → `.env` key not loaded, restart uvicorn (dotenv doesn't hot-reload)
- **"Celery task stuck in PENDING forever"** → worker isn't running, or wrong queue name — check `task_routes` in `celery_app.py`
- **"viaSocket webhook returns 404"** → tenant's webhook URL isn't set in `tenants.viasocket_webhook_url` — this is per-tenant config, not global env var
- **"Docker Postgres port conflict"** → you probably have EvalPro's Postgres running too, change port mapping in `docker-compose.override.yml`
- **Generated test file fails but LLM says it passed** → sandbox validation step didn't run (check `SANDBOX_VALIDATION=true` in `.env`), never trust ungenerated-and-unvalidated test output in a demo

## Test data / demo prep

- Seed script: `python scripts/seed_demo_tenant.py` — creates a demo tenant + sample GitHub repo webhook config
- Demo repo for changelog/docs testing: use a small public repo, don't demo against a huge monorepo (slow LLM context)
- For the notebook-to-blog demo, keep a pre-tested `.ipynb` in `demo_assets/` — don't discover mid-demo that a notebook has a broken cell

## Team sync protocol

- Contract changes (job status shape, module interface, event names) → post in team channel BEFORE merging, not after
- Daily: 10-min sync on what's blocking cross-role work (e.g. Dev 2 needs a field Dev 3 hasn't added yet)
- Merge order for demo day: Dev 3's core + DB first → Dev 1's modules → Dev 2's frontend wiring last, since frontend depends on both
