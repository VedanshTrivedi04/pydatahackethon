# Handover — Frontend Developer (Dev 2)

Read SKILL.md first for shared contracts. This file is your scope only.

## Your mission

Build the dashboard: job history, live job status, docs preview, and the approve/reject flow for notebook-to-blog drafts. Plus a simple landing page for the demo.

## Your directory

```
frontend/
  src/
    api/client.ts        # typed client against Dev 3's OpenAPI schema
    pages/
      Dashboard.tsx
      JobDetail.tsx
      DocsPreview.tsx
      Landing.tsx
    components/
      JobCard.tsx
      StatusBadge.tsx
      ApproveRejectPanel.tsx
```

## Stack

React 18 + Vite + TypeScript, Tailwind for styling. Keep it lightweight — this is a hackathon dashboard, not a full product, but should still look clean and enterprise-ish (given the track theme).

## Your only contract: the Jobs API

You build against these endpoints only — never assume DB structure, always go through the API:

```
GET  /api/v1/jobs?tenant_id=&module=&status=   -> paginated job list
GET  /api/v1/jobs/{job_id}                     -> full job detail + result
POST /api/v1/jobs/{job_id}/approve             -> notebook-to-blog only
POST /api/v1/jobs/{job_id}/reject
GET  /api/v1/jobs/{job_id}/artifacts/{artifact_id}  -> download/preview a generated file
```

Auth: every request needs `Authorization: Bearer <tenant_api_key>` header — Dev 3 will give you a demo key.

## Screens to build

### 1. Dashboard (main view)
- List of jobs across all 5 modules, filterable by module + status
- Status badges: `queued` (gray), `running` (blue, maybe pulse animation), `success` (green), `failed` (red), `partial` (amber)
- Click a job → JobDetail

### 2. Job detail
- Show module type, input summary, timestamps, and the result
- For test-gen: show generated test code with syntax highlighting (use `prism-react-renderer` or similar)
- For docs-gen: render the Markdown output
- For changelog: render the release notes Markdown
- For notebook-to-blog: render the blog draft + show ApproveRejectPanel

### 3. Approve/reject panel (notebook-to-blog specific)
- Two buttons: Approve → `POST /jobs/{id}/approve` (this triggers viaSocket publish to LinkedIn/X on the backend — you just call the endpoint and show a success toast)
- Reject → same pattern, with an optional feedback text field passed in the request body
- This is the "human-in-the-loop" feature the brief specifically calls out — make it visually clear this is a real gate, not just a formality

### 4. Landing page
- Simple: what ShipFaster does, the 5 modules as cards, a "connect your repo" CTA (can be a fake button for demo purposes if OAuth isn't wired in time)

## Polling vs websockets

For the hackathon, don't build websockets — poll `GET /jobs/{id}` every 2-3 seconds while status is `queued`/`running`, stop polling once terminal. Simple `useEffect` + `setInterval`, cleared on unmount. If there's spare time later, Dev 3 can add an SSE endpoint and you swap polling for that — but don't block on it.

## Things to confirm with Dev 3 before building

- Exact shape of `result` field per module type (it differs — test-gen returns code, changelog returns Markdown, etc.) — ask for a sample JSON response per module before you start typing components
- Whether pagination is cursor-based or offset-based
- Rate limits on the API (so you don't hammer it while polling)

## What NOT to do

- Don't call the DB or Celery directly — API only
- Don't hardcode tenant IDs — pull from auth context
- Don't build your own state management library — React Query (`@tanstack/react-query`) for server state is enough for this scope
