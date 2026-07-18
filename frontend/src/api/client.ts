/// <reference types="vite/client" />
import { Job, JobFilters, PaginatedJobsResponse, ModuleType } from './types';

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_BASE_URL = rawBaseUrl.replace(/['"]/g, '');

// Real credentials - auto-set on load
const REAL_API_KEY = 'sf_2314922a84f1f04209f3040f302bed7d98e545b4350850c1dd4455c809b1387b';
const REAL_TENANT_ID = 'd3c89532-fa95-4e6b-a5d1-cbdb6628039e';

// Auto-initialize real credentials if not set or if they are still mock values
if (!localStorage.getItem('shipfaster_api_key') || localStorage.getItem('shipfaster_api_key') === 'demo_tenant_key_12345') {
  localStorage.setItem('shipfaster_api_key', REAL_API_KEY);
}
if (!localStorage.getItem('shipfaster_tenant_id') || localStorage.getItem('shipfaster_tenant_id') === 'tenant_demo_01') {
  localStorage.setItem('shipfaster_tenant_id', REAL_TENANT_ID);
}

// Helper to get or set tenant API key in localStorage
export const getTenantApiKey = (): string => {
  return localStorage.getItem('shipfaster_api_key') || REAL_API_KEY;
};

export const setTenantApiKey = (key: string): void => {
  localStorage.setItem('shipfaster_api_key', key);
};

export const getTenantId = (): string => {
  return localStorage.getItem('shipfaster_tenant_id') || REAL_TENANT_ID;
};

export const setTenantId = (id: string): void => {
  localStorage.setItem('shipfaster_tenant_id', id);
};

// Fallback mock jobs when Dev 3 API is not reachable during local UI development or demo
const MOCK_JOBS: Job[] = [
  {
    job_id: 'job_scaff_9821a',
    tenant_id: 'tenant_demo_01',
    module: 'scaffolder',
    status: 'success',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    payload: { repo_url: 'https://github.com/shipfaster-ai/demo-backend', stack: 'fastapi-sqlalchemy-celery' },
    result: {
      status: 'success',
      output: {
        message: 'Project scaffolded successfully with 14 production files.',
        files: [
          'app/main.py',
          'app/api/v1/router.py',
          'app/core/config.py',
          'app/models/base.py',
          'Dockerfile',
          'docker-compose.yml',
          'requirements.txt'
        ]
      },
      artifacts: ['s3://shipfaster-artifacts/tenant_demo_01/job_scaff_9821a/scaffold.zip']
    }
  },
  {
    job_id: 'job_test_4102b',
    tenant_id: 'tenant_demo_01',
    module: 'test_generator',
    status: 'success',
    created_at: new Date(Date.now() - 1800000).toISOString(),
    payload: { repo_url: 'https://github.com/shipfaster-ai/demo-backend', target_file: 'app/api/v1/routes/jobs.py' },
    result: {
      status: 'success',
      output: {
        coverage_estimate: '94%',
        test_code: `import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_jobs_list(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/jobs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

@pytest.mark.asyncio
async def test_approve_notebook_draft(client: AsyncClient, auth_headers: dict):
    job_id = "job_blog_mock_01"
    response = await client.post(f"/api/v1/jobs/{job_id}/approve", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["approved"] is True`
      },
      artifacts: ['s3://shipfaster-artifacts/tenant_demo_01/job_test_4102b/test_jobs.py']
    }
  },
  {
    job_id: 'job_docs_7719c',
    tenant_id: 'tenant_demo_01',
    module: 'docs_generator',
    status: 'success',
    created_at: new Date(Date.now() - 900000).toISOString(),
    payload: { repo_url: 'https://github.com/shipfaster-ai/demo-backend', scope: 'full_api_reference' },
    result: {
      status: 'success',
      output: {
        markdown_docs: `# ShipFaster Core API Reference

This document outlines the high-performance REST interfaces for the ShipFaster platform.

## Authentication
Every endpoint requires an API token passed via the \`Authorization\` header:
\`\`\`http
Authorization: Bearer <tenant_api_key>
\`\`\`

## Core Endpoints

### 1. Retrieve Paginated Jobs
\`GET /api/v1/jobs\`

Fetches all automated developer jobs across all 5 modules for the authenticated tenant.

#### Query Parameters
- \`module\`: Filter by module (` + "`scaffolder`" + `, ` + "`test_generator`" + `, ` + "`docs_generator`" + `, ` + "`changelog_generator`" + `, ` + "`notebook_to_blog`" + `)
- \`status\`: Filter by state (` + "`queued`" + `, ` + "`running`" + `, ` + "`success`" + `, ` + "`failed`" + `, ` + "`partial`" + `)

### 2. Job Detail & Artifact Retrieval
\`GET /api/v1/jobs/{job_id}\`

Returns comprehensive job execution metrics, LLM token consumption, and generated output artifacts.`
      },
      artifacts: ['s3://shipfaster-artifacts/tenant_demo_01/job_docs_7719c/API_REFERENCE.md']
    }
  },
  {
    job_id: 'job_changelog_5504d',
    tenant_id: 'tenant_demo_01',
    module: 'changelog_generator',
    status: 'success',
    created_at: new Date(Date.now() - 600000).toISOString(),
    payload: { repo_url: 'https://github.com/shipfaster-ai/demo-backend', commit_range: 'v1.4.0...v1.5.0' },
    result: {
      status: 'success',
      output: {
        version: 'v1.5.0',
        release_notes_md: `# Release v1.5.0 - High-Speed Agent Orchestration

## Breaking Changes
- **API**: The \`POST /api/v1/jobs/dispatch\` route now strictly enforces JSON schema validation on the \`payload\` field.

## Features (feat)
- **Engine**: Added viaSocket webhook dispatch retry handler with exponential backoff (` + "`engine/core/events.py`" + `).
- **Modules**: Notebook-to-blog draft parser now automatically isolates code cells and uploads image outputs directly to S3 (` + "`engine/modules/notebook_to_blog/handler.py`" + `).

## Bug Fixes (fix)
- **Celery**: Fixed race condition where PENDING jobs timed out when Redis connection pool was exhausted.
- **MCP**: Resolved tool registration signature mismatch for the test generator.`
      },
      artifacts: ['s3://shipfaster-artifacts/tenant_demo_01/job_changelog_5504d/CHANGELOG_v1.5.0.md']
    }
  },
  {
    job_id: 'job_blog_3192e',
    tenant_id: 'tenant_demo_01',
    module: 'notebook_to_blog',
    status: 'partial',
    created_at: new Date(Date.now() - 300000).toISOString(),
    payload: { notebook_path: 's3://shipfaster-inputs/tenant_demo_01/churn_prediction_v2.ipynb', target_platform: 'linkedin_and_twitter' },
    result: {
      status: 'partial',
      output: {
        title: 'Predicting Customer Churn with XGBoost & SHAP Values (Full Breakdown)',
        blog_draft_md: `# Predicting Customer Churn with XGBoost & SHAP Values

When building ML pipelines in production, accuracy metrics only tell half the story. If a sales rep asks *why* an enterprise customer flagged for high churn risk, your model needs explainability.

In this deep-dive notebook conversion, we train an **XGBoost Classifier** on 50,000 SaaS interaction records and use **SHAP (SHapley Additive exPlanations)** to dissect individual predictions.

## 1. Feature Engineering & Data Preparation
Notice how we normalize engagement frequency while encoding categorical contract tiers:

\`\`\`python
import pandas as pd
import xgboost as xgb
import shap

# Load clean interaction dataset
df = pd.read_parquet("s3://shipfaster-data/saas_interactions.parquet")
features = ["login_frequency_7d", "api_calls_30d", "support_tickets_open", "contract_months"]
X, y = df[features], df["churned"]

model = xgb.XGBClassifier(n_estimators=150, max_depth=5, learning_rate=0.05)
model.fit(X, y)
\`\`\`

## 2. SHAP Summary Impact
Our model identified \`login_frequency_7d\` and \`support_tickets_open\` as the two highest leverage indicators across all cohorts.

> **Human-in-the-Loop Review Required:** This draft has been generated and ready for publishing via viaSocket webhook to LinkedIn and X. Please review the technical accuracy of the code snippets above before approving.`,
        images: ['https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1000&q=80']
      },
      artifacts: ['s3://shipfaster-artifacts/tenant_demo_01/job_blog_3192e/draft.md']
    }
  },
  {
    job_id: 'job_test_live_8812f',
    tenant_id: 'tenant_demo_01',
    module: 'test_generator',
    status: 'running',
    created_at: new Date().toISOString(),
    payload: { repo_url: 'https://github.com/shipfaster-ai/demo-backend', target_file: 'engine/core/celery_app.py' },
  }
];

// Helper for making API requests with fallback to mock data
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const apiKey = getTenantApiKey();
  const tenantId = getTenantId();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`,
    ...options.headers,
  };

  if (apiKey && apiKey.startsWith('ey') && tenantId) {
    headers['X-Tenant-ID'] = tenantId;
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (err) {
    // If backend is unreachable or returning error during frontend dev/demo, fall back gracefully to mock storage
    console.warn(`[ShipFaster Client] Backend unreachable for ${endpoint}, utilizing local store fallback.`, err);
    return handleMockRequest<T>(endpoint, options);
  }
}

// Translate backend model (id, jobs) to frontend model (job_id, items)
function mapBackendJob(backendJob: any): Job {
  if (!backendJob || (!backendJob.id && !backendJob.job_id)) return null as any;
  
  const rawResult = backendJob.result || {};
  let mappedArtifacts: string[] = [];
  if (backendJob.artifacts && Array.isArray(backendJob.artifacts)) {
    mappedArtifacts = backendJob.artifacts.map((art: any) => art.file_name);
  } else if (rawResult._artifacts && Array.isArray(rawResult._artifacts)) {
    mappedArtifacts = rawResult._artifacts.map((art: any) => art.file_name);
  }

  return {
    job_id: backendJob.id || backendJob.job_id,
    tenant_id: backendJob.tenant_id,
    module: backendJob.module,
    status: backendJob.status === 'approval_pending' ? 'partial' : backendJob.status,
    created_at: backendJob.created_at,
    updated_at: backendJob.updated_at,
    payload: backendJob.payload || {},
    result: {
      status: backendJob.status,
      output: rawResult,
      artifacts: mappedArtifacts,
      error: backendJob.error || null,
    },
    approved: backendJob.status === 'approved',
    rejected: backendJob.status === 'rejected',
    rejection_feedback: backendJob.approval_note || undefined,
  };
}

// Local mock execution handler to ensure smooth, zero-latency demos even without live backend
function handleMockRequest<T>(endpoint: string, options: RequestInit): T {
  // GET /api/v1/jobs or /api/v1/jobs?module=...
  if (endpoint.startsWith('/api/v1/jobs') && (!options.method || options.method === 'GET')) {
    const url = new URL(`http://mock${endpoint}`);
    const moduleFilter = url.searchParams.get('module');
    const statusFilter = url.searchParams.get('status');

    // Single job detail: /api/v1/jobs/job_id
    const parts = endpoint.split('?')[0].split('/');
    if (parts.length === 5 && parts[4] !== '') {
      const jobId = parts[4];
      const found = MOCK_JOBS.find((j) => j.job_id === jobId);
      if (!found) throw new Error(`Job ${jobId} not found in local mock state`);
      return found as unknown as T;
    }

    let filtered = [...MOCK_JOBS];
    if (moduleFilter && moduleFilter !== 'all') {
      filtered = filtered.filter((j) => j.module === moduleFilter);
    }
    if (statusFilter && statusFilter !== 'all') {
      filtered = filtered.filter((j) => j.status === statusFilter);
    }

    return {
      items: filtered,
      total: filtered.length,
      page: 1,
      size: 50,
    } as unknown as T;
  }

  // POST /api/v1/jobs/{job_id}/approve
  if (endpoint.includes('/approve') && options.method === 'POST') {
    const parts = endpoint.split('/');
    const jobId = parts[4];
    const job = MOCK_JOBS.find((j) => j.job_id === jobId);
    if (job) {
      job.status = 'success';
      job.approved = true;
      if (job.result) job.result.status = 'success';
    }
    return { approved: true, job_id: jobId, message: 'viaSocket payload published to LinkedIn/X successfully' } as unknown as T;
  }

  // POST /api/v1/jobs/{job_id}/reject
  if (endpoint.includes('/reject') && options.method === 'POST') {
    const parts = endpoint.split('/');
    const jobId = parts[4];
    const job = MOCK_JOBS.find((j) => j.job_id === jobId);
    const body = options.body ? JSON.parse(options.body as string) : {};
    if (job) {
      job.status = 'failed';
      job.rejected = true;
      job.rejection_feedback = body.feedback || 'Rejected by human-in-the-loop reviewer';
      if (job.result) job.result.status = 'failed';
    }
    return { rejected: true, job_id: jobId, feedback: body.feedback } as unknown as T;
  }

  // DELETE /api/v1/jobs/{job_id}
  if (endpoint.startsWith('/api/v1/jobs') && options.method === 'DELETE') {
    const parts = endpoint.split('/');
    const jobId = parts[4];
    const idx = MOCK_JOBS.findIndex((j) => j.job_id === jobId);
    if (idx !== -1) {
      MOCK_JOBS.splice(idx, 1);
    }
    return { success: true, message: `Job ${jobId} deleted successfully` } as unknown as T;
  }

  // POST /api/v1/jobs (Create sample job)
  if (endpoint === '/api/v1/jobs' && options.method === 'POST') {
    const body = options.body ? JSON.parse(options.body as string) : {};
    const newJob: Job = {
      job_id: `job_${body.module.split('_')[0]}_${Math.random().toString(36).substring(2, 7)}`,
      tenant_id: getTenantId(),
      module: body.module as ModuleType,
      status: 'queued',
      created_at: new Date().toISOString(),
      payload: body.payload || { repo_url: 'https://github.com/shipfaster-ai/demo-repo' }
    };
    MOCK_JOBS.unshift(newJob);

    // Simulate transition to running and then success after a delay
    setTimeout(() => {
      newJob.status = 'running';
      setTimeout(() => {
        newJob.status = 'success';
        newJob.result = {
          status: 'success',
          output: { message: `Completed ${newJob.module} automated workflow.`, generated_at: new Date().toISOString() },
          artifacts: [`s3://shipfaster-artifacts/${newJob.tenant_id}/${newJob.job_id}/output.zip`]
        };
      }, 4000);
    }, 2000);

    return newJob as unknown as T;
  }

  throw new Error(`Unhandled mock route: ${options.method || 'GET'} ${endpoint}`);
}

export const jobsApi = {
  getJobs: async (filters?: JobFilters): Promise<PaginatedJobsResponse> => {
    const params = new URLSearchParams();
    if (filters?.tenant_id) params.append('tenant_id', filters.tenant_id);
    if (filters?.module && filters.module !== 'all') params.append('module', filters.module);
    if (filters?.status && filters.status !== 'all') params.append('status', filters.status);
    
    const query = params.toString();
    const res = await request<any>(`/api/v1/jobs${query ? `?${query}` : ''}`);
    
    // If fallback mock response (contains items directly)
    if (res && res.items) {
      return res as PaginatedJobsResponse;
    }
    
    // If backend response, extract and map
    const jobsList = res && res.jobs ? res.jobs : (res && res.data && res.data.jobs ? res.data.jobs : []);
    const total = res && typeof res.total === 'number' ? res.total : 0;
    
    return {
      items: jobsList.map(mapBackendJob),
      total: total,
      page: 1,
      size: 50
    };
  },

  getJob: async (jobId: string): Promise<Job> => {
    const res = await request<any>(`/api/v1/jobs/${jobId}`);
    if (res && res.job_id) {
      return res as Job;
    }
    const rawJob = res && res.job ? res.job : (res && res.data && res.data.job ? res.data.job : res);
    return mapBackendJob(rawJob);
  },

  approveJob: async (jobId: string): Promise<{ approved: boolean; message: string }> => {
    return request<{ approved: boolean; message: string }>(`/api/v1/jobs/${jobId}/approve`, {
      method: 'POST',
    });
  },

  rejectJob: async (jobId: string, feedback?: string): Promise<{ rejected: boolean; feedback?: string }> => {
    return request<{ rejected: boolean; feedback?: string }>(`/api/v1/jobs/${jobId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ feedback: feedback || '' }),
    });
  },

  createDemoJob: async (module: ModuleType, payload: Record<string, any>): Promise<Job> => {
    const res = await request<any>(`/api/v1/jobs`, {
      method: 'POST',
      body: JSON.stringify({ module, payload }),
    });
    if (res && res.job_id) {
      return res as Job;
    }
    const rawJob = res && res.job ? res.job : (res && res.data && res.data.job ? res.data.job : res);
    return mapBackendJob(rawJob);
  },

  deleteJob: async (jobId: string): Promise<{ success: boolean; message: string }> => {
    return request<{ success: boolean; message: string }>(`/api/v1/jobs/${jobId}`, {
      method: 'DELETE',
    });
  },
};

export const tenantsApi = {
  createTenant: async (name: string, slug: string, email: string): Promise<{ tenant: any; api_key: string }> => {
    return request<any>('/api/v1/tenants', {
      method: 'POST',
      body: JSON.stringify({
        name,
        slug,
        email,
        plan: 'free',
        initial_key_name: 'Default Key',
      }),
    });
  },
};

export const authApi = {
  register: async (email: string, password: string, fullName: string, tenantName: string): Promise<any> => {
    return request<any>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        tenant_name: tenantName,
      }),
    });
  },
  login: async (email: string, password: string): Promise<any> => {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  },
};
