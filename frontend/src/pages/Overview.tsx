import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Terminal, Cpu, Box, Code2, FileText, GitCommit, FileSpreadsheet, Play, Sparkles, Zap, Shield, Database, Network } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { jobsApi, getTenantId } from '../api/client';

export const Overview: React.FC = () => {
  const navigate = useNavigate();
  const tenantId = getTenantId();

  // Fetch jobs to calculate real stats
  const { data } = useQuery({
    queryKey: ['jobs_overview'],
    queryFn: () => jobsApi.getJobs(),
    refetchInterval: 5000,
  });

  const jobs = data?.items || [];
  const activeJobs = jobs.filter(j => j.status === 'queued' || j.status === 'running').length;
  const successJobs = jobs.filter(j => j.status === 'success').length;
  const totalJobs = jobs.length;
  const successRate = totalJobs > 0 ? Math.round((successJobs / totalJobs) * 100) : 100;

  const handleRunModule = (module: string) => {
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-[#030303] text-white py-10 px-6 lg:px-12 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="relative rounded-2xl overflow-hidden mb-8 border border-[#00f0ff]/20 bg-gradient-to-r from-[#141414] to-[#0a0a0a] p-8 shadow-[0_0_30px_rgba(0,240,255,0.03)]">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Sparkles className="w-40 h-40 text-[#00f0ff]" />
        </div>
        <div className="relative z-10">
          <span className="font-mono text-xs text-[#00f0ff] uppercase tracking-widest flex items-center gap-1.5 mb-2">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" /> Active Workspace Overview
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2">
            Welcome back to ShipFaster
          </h1>
          <p className="text-sm text-neutral-400 font-mono max-w-xl">
            You are authenticated in Tenant Space: <code className="text-[#00f0ff] bg-[#1a1a1a] px-1.5 py-0.5 rounded">{tenantId}</code>
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
        <div className="glass-panel rounded-2xl p-5 border border-neutral-850 flex flex-col justify-between bg-[#0a0a0a]">
          <span className="text-xs font-mono text-neutral-500 uppercase tracking-wider block mb-1">Active Tasks</span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-3xl font-bold text-white font-mono">{activeJobs}</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">Running</span>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-5 border border-neutral-850 flex flex-col justify-between bg-[#0a0a0a]">
          <span className="text-xs font-mono text-neutral-500 uppercase tracking-wider block mb-1">Success Rate</span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-3xl font-bold text-white font-mono">{successRate}%</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">Verified</span>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-5 border border-neutral-850 flex flex-col justify-between bg-[#0a0a0a]">
          <span className="text-xs font-mono text-neutral-500 uppercase tracking-wider block mb-1">Total Jobs Run</span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-3xl font-bold text-white font-mono">{totalJobs}</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-neutral-800 text-neutral-400 border border-neutral-800 font-mono">All Time</span>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-5 border border-neutral-850 flex flex-col justify-between bg-[#0a0a0a]">
          <span className="text-xs font-mono text-neutral-500 uppercase tracking-wider block mb-1">Infrastructure Status</span>
          <div className="flex flex-col gap-1.5 mt-2 font-mono text-[10px] text-neutral-400">
            <div className="flex items-center gap-1.5 justify-between">
              <span className="flex items-center gap-1 text-neutral-500"><Database className="w-3 h-3" /> PostgreSQL</span>
              <span className="text-emerald-400 font-semibold">Online</span>
            </div>
            <div className="flex items-center gap-1.5 justify-between">
              <span className="flex items-center gap-1 text-neutral-500"><Network className="w-3 h-3" /> Redis Queue</span>
              <span className="text-emerald-400 font-semibold">Online</span>
            </div>
          </div>
        </div>
      </div>

      {/* Modules Overview */}
      <div className="mb-10">
        <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
          <Terminal className="w-5 h-5 text-[#00f0ff]" />
          Launch Automation Workspaces
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 hover:border-[#00f0ff]/40 transition-all flex flex-col justify-between bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#00f0ff]/10 border border-[#00f0ff]/30 flex items-center justify-center mb-4 text-[#00f0ff]">
                <Box className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-white text-base mb-1">Project Scaffolder</h4>
              <p className="text-xs text-neutral-400 leading-relaxed mb-4">
                Generate production FastAPI directories inside isolated zip archives instantly.
              </p>
            </div>
            <button
              onClick={() => handleRunModule('scaffolder')}
              className="mt-2 w-full py-2.5 rounded-xl bg-[#141414] hover:bg-[#00f0ff] hover:text-[#0a0a0a] text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Open Workspace
            </button>
          </div>

          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 hover:border-emerald-500/40 transition-all flex flex-col justify-between bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-4 text-emerald-400">
                <Code2 className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-white text-base mb-1">Pytest Generator</h4>
              <p className="text-xs text-neutral-400 leading-relaxed mb-4">
                Scan routes and write high-coverage unit tests with auto-mocked database models.
              </p>
            </div>
            <button
              onClick={() => handleRunModule('test_generator')}
              className="mt-2 w-full py-2.5 rounded-xl bg-[#141414] hover:bg-emerald-500 hover:text-white text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Open Workspace
            </button>
          </div>

          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 hover:border-violet-500/40 transition-all flex flex-col justify-between bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center mb-4 text-violet-400">
                <FileText className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-white text-base mb-1">Docs Generator</h4>
              <p className="text-xs text-neutral-400 leading-relaxed mb-4">
                Construct OpenAPI specs and clean markdown installation manuals automatically.
              </p>
            </div>
            <button
              onClick={() => handleRunModule('docs_generator')}
              className="mt-2 w-full py-2.5 rounded-xl bg-[#141414] hover:bg-violet-500 hover:text-white text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Open Workspace
            </button>
          </div>

          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 hover:border-amber-500/40 transition-all flex flex-col justify-between bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-4 text-amber-400">
                <GitCommit className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-white text-base mb-1">Changelog Builder</h4>
              <p className="text-xs text-neutral-400 leading-relaxed mb-4">
                Parse git commits, build conventional change summaries, and trigger webhooks.
              </p>
            </div>
            <button
              onClick={() => handleRunModule('changelog_generator')}
              className="mt-2 w-full py-2.5 rounded-xl bg-[#141414] hover:bg-amber-500 hover:text-white text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Open Workspace
            </button>
          </div>

          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 hover:border-pink-500/40 transition-all flex flex-col justify-between bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-pink-500/10 border border-pink-500/30 flex items-center justify-center mb-4 text-pink-400">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-white text-base mb-1">Notebook to Blog</h4>
              <p className="text-xs text-neutral-400 leading-relaxed mb-4">
                Convert Jupyter code blocks into developer posts with approval gates.
              </p>
            </div>
            <button
              onClick={() => handleRunModule('notebook_to_blog')}
              className="mt-2 w-full py-2.5 rounded-xl bg-[#141414] hover:bg-pink-500 hover:text-white text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Open Workspace
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
