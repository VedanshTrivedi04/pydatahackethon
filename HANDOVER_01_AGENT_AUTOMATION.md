# Handover — Agent & Automation Developer (Dev 1)

Read SKILL.md first for shared contracts. This file is your scope only.

## Your mission

Build the 5 automation modules, the MCP server that exposes them as LLM-callable tools, and the prompt/LLM logic that makes each module actually good — not just "wraps an API call."

## Your directories

```
engine/
  modules/
    scaffolder/handler.py
    test_generator/handler.py
    docs_generator/handler.py
    changelog_generator/handler.py
    notebook_to_blog/handler.py
  mcp/
    server.py
    tools.py
  prompts/
    scaffolder.py
    test_generator.py
    docs_generator.py
    changelog_generator.py
    notebook_to_blog.py
```

## The one rule that matters

Every module's `handler.py` exports:
```python
async def run(job_id: str, tenant_id: str, payload: dict) -> ModuleResult:
```
This is called by Dev 3's Celery worker. You never touch Celery, queue config, or the DB directly — call `engine.core.llm_client.complete()` and `engine.core.storage.save_artifact()` (both provided by Dev 3) instead of raw API/S3 calls. This keeps cost tracking and tenant isolation centralized.

## Module-by-module build notes

### 1. Scaffolder
- Input: `{"stack": "fastapi", "project_name": "..."}`
- No LLM call needed for MVP — Jinja2 template rendering from `templates/{stack}/`
- Output artifacts: zipped project skeleton
- Stretch: LLM customizes README based on a one-line project description

### 2. Test generator (the hardest, most demo-worthy one)
- Input: `{"file_content": "...", "repo_context": "..."}`
- Steps:
  1. `ast.parse()` the file, extract function signatures, branches (if/else, try/except, loops)
  2. Build prompt listing every branch that needs coverage — don't just say "write tests," enumerate what must be covered
  3. Call LLM, get pytest code back
  4. **Critical**: run the generated test in a sandboxed subprocess (Dev 3 provides `engine.core.sandbox.execute()`) before returning success
  5. If it fails, retry once with the error message fed back to the LLM ("this test failed with: ..., fix it")
- Never return `status: "success"` for unvalidated test code — return `"partial"` with a warning if validation is skipped

### 3. Docs generator
- Input: FastAPI/Flask/Django route file(s)
- For FastAPI, you already have OpenAPI schema — don't regenerate from scratch, enrich it: missing descriptions, example payloads, edge-case notes
- For Flask/Django, parse route decorators manually (regex or `ast`) since no OpenAPI exists natively
- Output: OpenAPI YAML + a rendered Markdown doc

### 4. Changelog generator
- Input: `{"commit_range": "v1.2.0..HEAD", "repo_url": "..."}`
- `git log --pretty=format:'%H|%s|%b'` parsed, grouped by conventional-commit prefix (feat/fix/chore/breaking)
- LLM writes human-readable release notes per group, flags breaking changes prominently
- This is your primary viaSocket event source — build the payload per the contract in SKILL.md (`event: "changelog.generated"`)

### 5. Notebook-to-blog
- `nbformat` to parse `.ipynb`, separate markdown cells / code cells / output images
- Images go to S3 via `engine.core.storage.save_artifact()`, get public URLs
- LLM restructures into blog narrative — preserve code blocks, rewrite prose transitions
- Output goes through the approve/reject flow (Dev 2's UI, Dev 3's API) before viaSocket publishes it — you don't publish directly

## MCP server

Wrap all 5 `run()` functions as MCP tools in `engine/mcp/tools.py`. Tool descriptions matter a lot — LLM agents pick tools based on description quality, be specific about what inputs each tool needs.

Also worth pairing with viaSocket's own MCP server (mentioned in the brief) so an agent using ShipFaster's MCP tools can also reach 2000+ external apps in the same session — check their docs for the server URL format, likely just another `mcp_servers` entry.

## Prompt engineering notes

- Keep system prompts in `/engine/prompts/*.py` as separate constants, not inline strings — makes iteration and eval easier
- For structured output (test code, changelog JSON), instruct the model to return ONLY the code/JSON, no preamble — you're parsing this programmatically
- Log every prompt + response pair during dev (strip in prod) so you can debug why a module produced bad output

## What NOT to do

- Don't call `anthropic` SDK directly — always through `llm_client.complete()`
- Don't write to the DB directly — `ModuleResult` is your only output channel
- Don't build retry/queue logic — Celery handles that, you just raise or return `"failed"`
