import React, { useState } from 'react';
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
  
  // Scaffolder specific states
  const [newProjectName, setNewProjectName] = useState('my_fastapi_backend');
  const [newDescription, setNewDescription] = useState('A simple FastAPI backend skeleton.');
  
  // Other module states
  const [newRepoUrl, setNewRepoUrl] = useState('https://github.com/shipfaster-ai/pydata-hackathon-demo');
  const [newTargetFile, setNewTargetFile] = useState('engine/core/models.py');
  const [newCommitRange, setNewCommitRange] = useState('v1.4.0...v1.5.0');
  const [newNotebookPath, setNewNotebookPath] = useState('notebooks/churn_prediction_v2.ipynb');
  
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
      let payload: Record<string, any> = {};

      if (newModule === 'scaffolder') {
        payload = {
          stack: 'fastapi',
          project_name: newProjectName,
          description: newDescription,
        };
      } else {
        payload = {
          repo_url: newRepoUrl,
        };
        if (newModule === 'test_generator') {
          payload.target_file = newTargetFile;
        }
        if (newModule === 'changelog_generator') {
          payload.commit_range = newCommitRange;
        }
        if (newModule === 'notebook_to_blog') {
          payload.notebook_path = newNotebookPath;
          payload.target_platform = 'linkedin_and_twitter';
        }
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

  const handleDeleteJob = async (jobId: string) => {
    if (!window.confirm("Are you sure you want to delete this job?")) return;
    try {
      await jobsApi.deleteJob(jobId);
      refetch();
    } catch (err: any) {
      alert(`Error deleting job: ${err.message}`);
    }
  };

  const jobs = data?.items || [];

  return (
    <div className="min-h-screen bg-[#030303] text-white py-10 px-6 lg:px-12 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-8 pb-6 border-b border-[#1f1f1f]">
        <div>
          <div className="inline-flex items-center gap-2 font-mono text-xs text-[#00f0ff] uppercase tracking-wider mb-1">
            <Terminal className="w-3.5 h-3.5" /> Dev 2 & Dev 3 API Contract
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Automated Jobs Monitor
            <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-[#141414] text-neutral-450 border border-[#242424]">
              {data?.total ?? 0} total
            </span>
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-2.5 rounded-xl bg-[#141414] hover:bg-[#1f1f1f] border border-[#242424] text-neutral-305 hover:text-white transition-all"
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
          <button
            onClick={() => setModuleFilter('all')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              moduleFilter === 'all'
                ? 'bg-[#242424] text-[#00f0ff] shadow-sm font-semibold'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            All Modules
          </button>
          <button
            onClick={() => setModuleFilter('scaffolder')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              moduleFilter === 'scaffolder'
                ? 'bg-[#242424] text-[#00f0ff] shadow-sm font-semibold'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            Scaffolder
          </button>
          <button
            onClick={() => setModuleFilter('test_generator')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              moduleFilter === 'test_generator'
                ? 'bg-[#242424] text-emerald-455 shadow-sm font-semibold'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            Test Gen
          </button>
          <button
            onClick={() => setModuleFilter('docs_generator')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              moduleFilter === 'docs_generator'
                ? 'bg-[#242424] text-violet-400 shadow-sm font-semibold'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            Docs Gen
          </button>
          <button
            onClick={() => setModuleFilter('changelog_generator')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              moduleFilter === 'changelog_generator'
                ? 'bg-[#242424] text-amber-400 shadow-sm font-semibold'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            Changelog
          </button>
          <button
            onClick={() => setModuleFilter('notebook_to_blog')}
            className={`px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              moduleFilter === 'notebook_to_blog'
                ? 'bg-[#242424] text-pink-400 shadow-sm font-semibold'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            Notebook
          </button>
        </div>

        {/* Status Filter Selector */}
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" /> Status:
          </span>
          <div className="flex bg-[#141414] p-1 rounded-xl border border-[#1f1f1f]">
            <button
              onClick={() => setStatusFilter('all')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === 'all' ? 'bg-[#242424] text-white' : 'text-neutral-405 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setStatusFilter('running')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === 'running' ? 'bg-[#242424] text-white' : 'text-neutral-405 hover:text-white'
              }`}
            >
              Running
            </button>
            <button
              onClick={() => setStatusFilter('success')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === 'success' ? 'bg-[#242424] text-white' : 'text-neutral-405 hover:text-white'
              }`}
            >
              Success
            </button>
            <button
              onClick={() => setStatusFilter('failed')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === 'failed' ? 'bg-[#242424] text-white' : 'text-neutral-405 hover:text-white'
              }`}
            >
              Failed
            </button>
          </div>
        </div>
      </div>

      {/* Jobs Grid / Empty State */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 className="w-8 h-8 text-[#00f0ff] animate-spin" />
          <span className="font-mono text-sm text-neutral-400">Fetching workspace jobs...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 rounded-2xl border border-neutral-850 bg-[#0a0a0a] text-center p-8">
          <Layers className="w-12 h-12 text-neutral-600 mb-4" />
          <h3 className="font-bold text-white text-base mb-1">No active jobs found</h3>
          <p className="text-xs text-neutral-500 max-w-xs mb-6">
            There are no automation jobs matching the active filters in this tenant space.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2.5 rounded-xl bg-[#1f1f1f] text-neutral-300 hover:text-white text-xs font-mono"
          >
            Spawn First Demo Task
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {jobs.map((job) => (
            <JobCard 
              key={job.job_id} 
              job={job} 
              onDelete={() => handleDeleteJob(job.job_id)}
            />
          ))}
        </div>
      )}

      {/* Spawn Demo Job Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-8 border border-neutral-800 shadow-[0_0_50px_rgba(0,240,255,0.08)] bg-[#050505]/95">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white flex items-center gap-2.5">
                <Sparkles className="w-5 h-5 text-[#00f0ff]" />
                Dispatch Automated Task to Celery
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="p-2 hover:bg-neutral-900 rounded-lg text-neutral-500 hover:text-white transition-all text-xs">✕</button>
            </div>

            <form onSubmit={handleCreateJob} className="space-y-5 font-mono text-xs">
              <div>
                <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Module Type</label>
                <select
                  value={newModule}
                  onChange={(e) => setNewModule(e.target.value as ModuleType)}
                  className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3 text-white outline-none"
                >
                  <option value="scaffolder">Project Scaffolder (`run()` interface)</option>
                  <option value="test_generator">Async Pytest Generator (`target_file`)</option>
                  <option value="docs_generator">OpenAPI & Architecture Docs Generator</option>
                  <option value="changelog_generator">Conventional Changelog & viaSocket Hook</option>
                  <option value="notebook_to_blog">Jupyter Notebook to Blog (Human Gate)</option>
                </select>
              </div>

              {newModule === 'scaffolder' ? (
                <>
                  <div>
                    <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Project Name</label>
                    <input
                      type="text"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Project Description</label>
                    <textarea
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      rows={3}
                      className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800 resize-none"
                      required
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Target Repository URL</label>
                    <input
                      type="text"
                      value={newRepoUrl}
                      onChange={(e) => setNewRepoUrl(e.target.value)}
                      className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                      required
                    />
                  </div>

                  {newModule === 'test_generator' && (
                    <div>
                      <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Target File Path</label>
                      <input
                        type="text"
                        value={newTargetFile}
                        onChange={(e) => setNewTargetFile(e.target.value)}
                        className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                        required
                      />
                    </div>
                  )}

                  {newModule === 'changelog_generator' && (
                    <div>
                      <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Commit Range</label>
                      <input
                        type="text"
                        value={newCommitRange}
                        onChange={(e) => setNewCommitRange(e.target.value)}
                        className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                        required
                      />
                    </div>
                  )}

                  {newModule === 'notebook_to_blog' && (
                    <div>
                      <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Target Notebook Path</label>
                      <input
                        type="text"
                        value={newNotebookPath}
                        onChange={(e) => setNewNotebookPath(e.target.value)}
                        className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                        required
                      />
                    </div>
                  )}
                </>
              )}

              <div className="pt-3 flex gap-3 font-sans">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-3.5 rounded-xl bg-neutral-900 text-neutral-300 hover:text-white text-xs font-semibold border border-neutral-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="flex-1 px-4 py-3.5 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#7c3aed] text-black font-bold text-xs tracking-wider uppercase transition-all shadow-[0_0_20px_rgba(0,240,255,0.25)] flex items-center justify-center gap-2 active:scale-[0.98] disabled:opacity-50"
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
