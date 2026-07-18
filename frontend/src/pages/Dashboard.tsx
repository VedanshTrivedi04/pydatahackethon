import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { jobsApi } from '../api/client';
import { Job, ModuleType, JobStatus } from '../api/types';
import { JobCard } from '../components/dashboard/JobCard';
import { Terminal, Filter, Plus, RefreshCw, Layers, Sparkles, Loader2 } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [moduleFilter, setModuleFilter] = useState<ModuleType | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newModule, setNewModule] = useState<ModuleType>('scaffolder');
  const [newRepoUrl, setNewRepoUrl] = useState('https://github.com/shipfaster-ai/pydata-hackathon-demo');
  const [newTargetFile, setNewTargetFile] = useState('engine/core/models.py');
  const [createLoading, setCreateLoading] = useState(false);

  // Poll jobs list every 3 seconds to capture live Celery transitions
  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['jobs', moduleFilter, statusFilter],
    queryFn: () => jobsApi.getJobs({
      module: moduleFilter === 'all' ? undefined : moduleFilter,
      status: statusFilter === 'all' ? undefined : statusFilter,
    }),
    refetchInterval: 3000,
  });

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      const payload: Record<string, any> = { repo_url: newRepoUrl };
      if (newModule === 'test_generator') payload.target_file = newTargetFile;
      if (newModule === 'changelog_generator') payload.commit_range = 'v1.4.0...v1.5.0';
      if (newModule === 'notebook_to_blog') {
        payload.notebook_path = 's3://shipfaster-inputs/churn_prediction_v2.ipynb';
        payload.target_platform = 'linkedin_and_twitter';
      }

      await jobsApi.createDemoJob(newModule, payload);
      setShowCreateModal(false);
      refetch();
    } catch (err: any) {
      alert(`Error creating job: ${err.message}`);
    } finally {
      setCreateLoading(false);
    }
  };

  const jobs = data?.items || [];

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white py-10 px-6 lg:px-12 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-8 pb-6 border-b border-[#1f1f1f]">
        <div>
          <div className="inline-flex items-center gap-2 font-mono text-xs text-[#00f0ff] uppercase tracking-wider mb-1">
            <Terminal className="w-3.5 h-3.5" /> Dev 2 & Dev 3 API Contract
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Automated Jobs Monitor
            <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-[#141414] text-neutral-400 border border-[#242424]">
              {data?.total ?? 0} total
            </span>
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-2.5 rounded-xl bg-[#141414] hover:bg-[#1f1f1f] border border-[#242424] text-neutral-300 hover:text-white transition-all"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${isRefetching ? 'animate-spin text-[#00f0ff]' : ''}`} />
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2.5 rounded-xl bg-[#00f0ff] hover:bg-[#00d0df] text-[#0a0a0a] font-bold text-xs tracking-wide transition-all shadow-[0_0_20px_rgba(0,240,255,0.3)] flex items-center gap-2"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            Spawn Demo Job
          </button>
        </div>
      </div>

      {/* Filter Tabs & Dropdowns */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
        {/* Module Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 bg-[#141414] p-1.5 rounded-xl border border-[#1f1f1f]">
          {(['all', 'scaffolder', 'test_generator', 'docs_generator', 'changelog_generator', 'notebook_to_blog'] as const).map((mod) => (
            <button
              key={mod}
              onClick={() => setModuleFilter(mod)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all capitalize ${
                moduleFilter === mod
                  ? 'bg-[#242424] text-[#00f0ff] font-semibold shadow-sm border border-[#00f0ff]/30'
                  : 'text-neutral-400 hover:text-white hover:bg-[#1f1f1f]'
              }`}
            >
              {mod === 'all' ? 'All Modules' : mod.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        {/* Status Dropdown */}
        <div className="flex items-center gap-2 shrink-0">
          <Filter className="w-4 h-4 text-neutral-400" />
          <span className="text-xs font-mono text-neutral-400">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as JobStatus | 'all')}
            className="bg-[#141414] border border-[#242424] focus:border-[#00f0ff] rounded-xl px-3 py-1.5 text-xs font-mono text-white outline-none transition-colors"
          >
            <option value="all">All Statuses</option>
            <option value="queued">Queued</option>
            <option value="running">Running</option>
            <option value="success">Success</option>
            <option value="partial">Partial Success</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Jobs Grid */}
      {isLoading ? (
        <div className="py-24 text-center flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#00f0ff]" />
          <p className="font-mono text-sm text-neutral-400">Polling Celery workers via REST API...</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-[#1f1f1f]">
          <Layers className="w-12 h-12 text-neutral-600 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-white mb-1">No Jobs Found</h3>
          <p className="text-xs text-neutral-400 font-mono max-w-sm mx-auto mb-6">
            No active or past automated tasks match your current filter settings.
          </p>
          <button
            onClick={() => { setModuleFilter('all'); setStatusFilter('all'); }}
            className="px-4 py-2 rounded-xl bg-[#1f1f1f] text-neutral-300 hover:text-white text-xs font-mono"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {jobs.map((job) => (
            <JobCard key={job.job_id} job={job} />
          ))}
        </div>
      )}

      {/* Spawn Demo Job Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-lg rounded-2xl p-6 border border-[#00f0ff]/40 shadow-[0_0_50px_rgba(0,240,255,0.15)]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[#00f0ff]" />
                Dispatch Automated Task to Celery
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-neutral-400 hover:text-white text-sm px-2 py-1">✕</button>
            </div>

            <form onSubmit={handleCreateJob} className="space-y-4 font-mono text-sm">
              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-400 mb-1.5">Module Type</label>
                <select
                  value={newModule}
                  onChange={(e) => setNewModule(e.target.value as ModuleType)}
                  className="w-full bg-[#0a0a0a] border border-[#242424] focus:border-[#00f0ff] rounded-xl px-3.5 py-2.5 text-white outline-none"
                >
                  <option value="scaffolder">Project Scaffolder (`run()` interface)</option>
                  <option value="test_generator">Async Pytest Generator (`target_file`)</option>
                  <option value="docs_generator">OpenAPI & Architecture Docs Generator</option>
                  <option value="changelog_generator">Conventional Changelog & viaSocket Hook</option>
                  <option value="notebook_to_blog">Jupyter Notebook to Blog (Human Gate)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-400 mb-1.5">Target Repository URL</label>
                <input
                  type="text"
                  value={newRepoUrl}
                  onChange={(e) => setNewRepoUrl(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-[#242424] focus:border-[#00f0ff] rounded-xl px-3.5 py-2 text-white text-xs outline-none"
                  required
                />
              </div>

              {newModule === 'test_generator' && (
                <div>
                  <label className="block text-xs uppercase tracking-wider text-neutral-400 mb-1.5">Target File Path</label>
                  <input
                    type="text"
                    value={newTargetFile}
                    onChange={(e) => setNewTargetFile(e.target.value)}
                    className="w-full bg-[#0a0a0a] border border-[#242424] focus:border-[#00f0ff] rounded-xl px-3.5 py-2 text-white text-xs outline-none"
                  />
                </div>
              )}

              <div className="pt-3 flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-[#1f1f1f] text-neutral-300 hover:text-white text-xs font-sans font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-[#00f0ff] hover:bg-[#00d0df] text-[#0a0a0a] text-xs font-sans font-bold shadow-[0_0_15px_rgba(0,240,255,0.3)] flex items-center justify-center gap-2"
                >
                  {createLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Dispatch Job'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
