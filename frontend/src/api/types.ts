export type ModuleType =
  | 'scaffolder'
  | 'test_generator'
  | 'docs_generator'
  | 'changelog_generator'
  | 'notebook_to_blog';

export type JobStatus = 'queued' | 'running' | 'success' | 'failed' | 'partial';

export interface ModuleResult {
  status: JobStatus;
  output: Record<string, any>;
  artifacts: string[];
  error?: string | null;
}

export interface Job {
  job_id: string;
  tenant_id: string;
  module: ModuleType;
  status: JobStatus;
  created_at: string;
  updated_at?: string;
  payload: Record<string, any>;
  result?: ModuleResult;
  approved?: boolean;
  rejected?: boolean;
  rejection_feedback?: string;
}

export interface PaginatedJobsResponse {
  items: Job[];
  total: number;
  page: number;
  size: number;
}

export interface JobFilters {
  tenant_id?: string;
  module?: ModuleType | 'all';
  status?: JobStatus | 'all';
}
