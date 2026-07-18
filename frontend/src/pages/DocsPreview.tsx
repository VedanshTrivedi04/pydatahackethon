import React, { useState } from 'react';
import { FileText, Copy, Check, Download, Layers, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export const DocsPreview: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'api' | 'architecture' | 'changelog'>('api');
  const [copied, setCopied] = useState(false);

  const docsData = {
    api: `# ShipFaster Core API Reference

This document outlines the high-performance REST interfaces for the ShipFaster platform, built against Dev 3's OpenAPI schema.

## Authentication
Every request requires an API token passed via the \`Authorization\` header:
\`\`\`http
Authorization: Bearer <tenant_api_key>
\`\`\`

## Core Endpoints

### 1. Retrieve Paginated Jobs
\`GET /api/v1/jobs\`

Fetches automated developer jobs across all 5 modules for the authenticated tenant.

#### Query Parameters
- \`module\`: Filter by module (\`scaffolder\`, \`test_generator\`, \`docs_generator\`, \`changelog_generator\`, \`notebook_to_blog\`)
- \`status\`: Filter by state (\`queued\`, \`running\`, \`success\`, \`failed\`, \`partial\`)

### 2. Job Detail & Artifact Retrieval
\`GET /api/v1/jobs/{job_id}\`

Returns comprehensive execution metrics, input payloads, and generated artifacts.

### 3. Notebook Draft Approval Gate
\`POST /api/v1/jobs/{job_id}/approve\`

Triggers Dev 3's viaSocket webhook to publish the approved markdown draft directly to LinkedIn and X.`,

    architecture: `# ShipFaster Engine Architecture

ShipFaster connects CLI, git webhooks, and MCP servers directly into a distributed Celery execution queue.

## System Topology

\`\`\`
CLI / Git Webhook / MCP Call
        ↓
Core Engine (FastAPI) — auth, tenant resolution, job dispatch
        ↓
Module Router → 5 modules (scaffolder, test_gen, docs_gen, changelog, notebook_to_blog)
        ↓
Celery Worker (Redis queue) — async LLM execution, retries
        ↓
PostgreSQL (job state) + S3 / MinIO (artifact files)
        ↓
viaSocket Webhook Dispatch → GitHub Release / Slack / LinkedIn
\`\`\`

## Multi-Tenancy Boundary
Every generated artifact and database record strictly enforces \`tenant_id\` isolation. No cross-tenant leakage occurs across concurrent Celery workers.`,

    changelog: `# Release v1.5.0 - High-Speed Agent Orchestration

## Breaking Changes
- **API**: The \`POST /api/v1/jobs/dispatch\` route now strictly enforces JSON schema validation on the \`payload\` field.

## Features (feat)
- **Engine**: Added viaSocket webhook dispatch retry handler with exponential backoff.
- **Modules**: Notebook-to-blog draft parser isolates code cells and uploads image outputs to S3.

## Bug Fixes (fix)
- **Celery**: Fixed race condition where PENDING jobs timed out when Redis connection pool was exhausted.
- **MCP**: Resolved tool registration signature mismatch for the test generator.`
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(docsData[activeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white py-10 px-6 lg:px-12 max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 pb-6 border-b border-[#1f1f1f]">
        <div>
          <div className="inline-flex items-center gap-2 font-mono text-xs text-[#00f0ff] uppercase tracking-wider mb-1">
            <Layers className="w-3.5 h-3.5" /> Module 03 & 04 Artifact Hub
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Documentation & Changelog Preview
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCopy}
            className="px-4 py-2 rounded-xl bg-[#141414] hover:bg-[#1f1f1f] border border-[#242424] text-xs font-mono text-neutral-300 hover:text-white flex items-center gap-2 transition-all"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied Markdown' : 'Copy Markdown'}
          </button>

          <button
            onClick={() => alert('Downloading markdown documentation artifact from S3...')}
            className="px-4 py-2 rounded-xl bg-[#00f0ff] hover:bg-[#00d0df] text-[#0a0a0a] text-xs font-bold font-sans flex items-center gap-2 shadow-[0_0_15px_rgba(0,240,255,0.25)] transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Download Artifact
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 mb-6 border-b border-[#1f1f1f] pb-3">
        <button
          onClick={() => setActiveTab('api')}
          className={`px-4 py-2 rounded-xl text-xs font-mono transition-all ${
            activeTab === 'api'
              ? 'bg-[#1f1f1f] text-[#00f0ff] font-semibold border border-[#00f0ff]/30 shadow-sm'
              : 'text-neutral-400 hover:text-white hover:bg-[#141414]'
          }`}
        >
          API Reference (`docs_generator`)
        </button>
        <button
          onClick={() => setActiveTab('architecture')}
          className={`px-4 py-2 rounded-xl text-xs font-mono transition-all ${
            activeTab === 'architecture'
              ? 'bg-[#1f1f1f] text-[#00f0ff] font-semibold border border-[#00f0ff]/30 shadow-sm'
              : 'text-neutral-400 hover:text-white hover:bg-[#141414]'
          }`}
        >
          System Topology
        </button>
        <button
          onClick={() => setActiveTab('changelog')}
          className={`px-4 py-2 rounded-xl text-xs font-mono transition-all ${
            activeTab === 'changelog'
              ? 'bg-[#1f1f1f] text-[#00f0ff] font-semibold border border-[#00f0ff]/30 shadow-sm'
              : 'text-neutral-400 hover:text-white hover:bg-[#141414]'
          }`}
        >
          Release v1.5.0 (`changelog_generator`)
        </button>
      </div>

      {/* Rendered Document View */}
      <div className="glass-panel rounded-2xl p-8 lg:p-10 border border-[#1f1f1f] prose prose-invert max-w-none font-sans leading-relaxed">
        <ReactMarkdown>{docsData[activeTab]}</ReactMarkdown>
      </div>
    </div>
  );
};
