import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Terminal, Cpu, Code2, FileText, GitCommit, FileSpreadsheet, Box, ArrowRight, Sparkles, Zap, Shield, Play } from 'lucide-react';
import { jobsApi } from '../api/client';
import { ModuleType } from '../api/types';

export const Landing: React.FC = () => {
  const navigate = useNavigate();
  const [demoLoading, setDemoLoading] = useState<ModuleType | null>(null);

  const handleLaunchDemoJob = async (module: ModuleType, payload: Record<string, any>) => {
    setDemoLoading(module);
    try {
      const job = await jobsApi.createDemoJob(module, payload);
      navigate(`/jobs/${job.job_id}`);
    } catch (err: any) {
      alert(`Error starting job: ${err.message}`);
    } finally {
      setDemoLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white overflow-hidden pb-24">
      {/* Background Subtle Tech Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f1f1f15_1px,transparent_1px),linear-gradient(to_bottom,#1f1f1f15_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Hero Section (Hero Discipline Lock: Max 2 lines headline, max 20 words subtext, CTA visible above fold) */}
      <section className="relative pt-24 pb-20 px-6 lg:px-12 max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#141414] border border-[#00f0ff]/30 text-xs font-mono text-[#00f0ff] mb-8 shadow-[0_0_20px_rgba(0,240,255,0.15)]">
          <Sparkles className="w-3.5 h-3.5" />
          <span>PyData Hackathon Track: Unified Agent & Automation Platform</span>
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight max-w-4xl mx-auto leading-[1.1] mb-6 font-sans">
          Ship Faster with Agentic Developer Automation.
        </h1>

        <p className="text-base sm:text-lg text-neutral-300 max-w-2xl mx-auto leading-relaxed mb-10 font-sans">
          Orchestrate 5 specialized LLM modules from CLI and MCP server, connected directly to viaSocket workflows.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/dashboard"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#00f0ff] hover:bg-[#00d0df] text-[#0a0a0a] font-bold text-sm tracking-wide transition-all shadow-[0_0_25px_rgba(0,240,255,0.4)] flex items-center justify-center gap-2"
          >
            <Terminal className="w-4 h-4" />
            Explore Live Dashboard
            <ArrowRight className="w-4 h-4" />
          </Link>

          <a
            href="#modules"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#141414] hover:bg-[#1f1f1f] border border-[#262626] hover:border-[#00f0ff]/40 text-neutral-200 font-semibold text-sm transition-all flex items-center justify-center gap-2"
          >
            <Cpu className="w-4 h-4 text-[#00f0ff]" />
            Test 5 AI Modules Live
          </a>
        </div>

        {/* Live Architecture Bar */}
        <div className="mt-16 pt-8 border-t border-[#1f1f1f] grid grid-cols-2 md:grid-cols-4 gap-6 text-left max-w-4xl mx-auto">
          <div>
            <span className="text-xs font-mono text-neutral-400 block uppercase tracking-wider">Orchestrator</span>
            <span className="text-sm font-semibold text-white">FastAPI Core + Celery</span>
          </div>
          <div>
            <span className="text-xs font-mono text-neutral-400 block uppercase tracking-wider">Queue & Storage</span>
            <span className="text-sm font-semibold text-white">Redis + PostgreSQL + S3</span>
          </div>
          <div>
            <span className="text-xs font-mono text-neutral-400 block uppercase tracking-wider">External Hooks</span>
            <span className="text-sm font-semibold text-[#00f0ff]">viaSocket Webhook Engine</span>
          </div>
          <div>
            <span className="text-xs font-mono text-neutral-400 block uppercase tracking-wider">Human-in-Loop</span>
            <span className="text-sm font-semibold text-emerald-400">Notebook Approval Gate</span>
          </div>
        </div>
      </section>

      {/* 5 Modules Showcase (Asymmetric 2-Column Showcase Layout, No 3-Equal-Card Slop) */}
      <section id="modules" className="relative px-6 lg:px-12 max-w-7xl mx-auto pt-10">
        <div className="mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-2">
            5 Automated Platform Modules
          </h2>
          <p className="text-sm text-neutral-400 font-mono">
            Trigger via CLI, Git hooks, or click below to launch instant sandboxed demo jobs on our Celery queue.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Module 1: Scaffolder (Large Asymmetric Span) */}
          <div className="md:col-span-7 glass-panel rounded-2xl p-8 border border-[#1f1f1f] hover:border-[#00f0ff]/50 transition-all flex flex-col justify-between group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-[#00f0ff]/10 border border-[#00f0ff]/30 flex items-center justify-center mb-6 text-[#00f0ff]">
                <Box className="w-6 h-6" />
              </div>
              <span className="font-mono text-xs text-[#00f0ff] uppercase tracking-wider">Module 01 / engine/modules/scaffolder</span>
              <h3 className="text-2xl font-bold text-white mt-1 mb-3">Full-Stack Project Scaffolder</h3>
              <p className="text-sm text-neutral-300 leading-relaxed mb-6">
                Analyzes repository intent and generates production-ready multi-layered architectures with FastAPI, SQLAlchemy models, Docker Compose services, and strict mypy verification.
              </p>
            </div>
            <div className="pt-6 border-t border-[#1f1f1f] flex items-center justify-between">
              <span className="font-mono text-xs text-neutral-400">Artifact: <code className="text-neutral-300 bg-[#0a0a0a] px-1.5 py-0.5 rounded">scaffold.zip</code></span>
              <button
                onClick={() => handleLaunchDemoJob('scaffolder', { repo_url: 'https://github.com/shipfaster-ai/fastapi-template', stack: 'fastapi-postgres-celery' })}
                disabled={demoLoading !== null}
                className="px-4 py-2 rounded-xl bg-[#1f1f1f] hover:bg-[#00f0ff] hover:text-[#0a0a0a] text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-sm disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                {demoLoading === 'scaffolder' ? 'Spawning Job...' : 'Run Scaffolder Demo'}
              </button>
            </div>
          </div>

          {/* Module 2: Test Generator */}
          <div className="md:col-span-5 glass-panel rounded-2xl p-8 border border-[#1f1f1f] hover:border-emerald-500/50 transition-all flex flex-col justify-between group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-6 text-emerald-400">
                <Code2 className="w-6 h-6" />
              </div>
              <span className="font-mono text-xs text-emerald-400 uppercase tracking-wider">Module 02 / engine/modules/test_generator</span>
              <h3 className="text-2xl font-bold text-white mt-1 mb-3">Async Pytest Suite Generator</h3>
              <p className="text-sm text-neutral-300 leading-relaxed mb-6">
                Inspects async route handlers and constructs high-coverage unit tests with isolated mock fixtures and sandboxed syntax validation.
              </p>
            </div>
            <div className="pt-6 border-t border-[#1f1f1f] flex items-center justify-between">
              <span className="font-mono text-xs text-neutral-400">Artifact: <code className="text-neutral-300 bg-[#0a0a0a] px-1.5 py-0.5 rounded">test_routes.py</code></span>
              <button
                onClick={() => handleLaunchDemoJob('test_generator', { repo_url: 'https://github.com/shipfaster-ai/fastapi-template', target_file: 'engine/api/routes/jobs.py' })}
                disabled={demoLoading !== null}
                className="px-4 py-2 rounded-xl bg-[#1f1f1f] hover:bg-emerald-500 hover:text-white text-xs font-semibold text-white transition-all flex items-center gap-2 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                {demoLoading === 'test_generator' ? 'Spawning Job...' : 'Run Test Generator'}
              </button>
            </div>
          </div>

          {/* Module 3: Docs Generator */}
          <div className="md:col-span-4 glass-panel rounded-2xl p-8 border border-[#1f1f1f] hover:border-violet-500/50 transition-all flex flex-col justify-between group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center mb-6 text-violet-400">
                <FileText className="w-6 h-6" />
              </div>
              <span className="font-mono text-xs text-violet-400 uppercase tracking-wider">Module 03 / docs_generator</span>
              <h3 className="text-xl font-bold text-white mt-1 mb-3">OpenAPI & Arch Docs</h3>
              <p className="text-sm text-neutral-300 leading-relaxed mb-6">
                Auto-documents REST endpoints, authentication schemas, and system boundary contracts in clean GitHub Flavored Markdown.
              </p>
            </div>
            <div className="pt-6 border-t border-[#1f1f1f] flex items-center justify-between">
              <span className="font-mono text-xs text-neutral-400">Output: Markdown</span>
              <button
                onClick={() => handleLaunchDemoJob('docs_generator', { repo_url: 'https://github.com/shipfaster-ai/fastapi-template', scope: 'full_api_reference' })}
                disabled={demoLoading !== null}
                className="px-3.5 py-2 rounded-xl bg-[#1f1f1f] hover:bg-violet-500 text-xs font-semibold text-white transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                Generate Docs
              </button>
            </div>
          </div>

          {/* Module 4: Changelog Generator */}
          <div className="md:col-span-4 glass-panel rounded-2xl p-8 border border-[#1f1f1f] hover:border-amber-500/50 transition-all flex flex-col justify-between group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-6 text-amber-400">
                <GitCommit className="w-6 h-6" />
              </div>
              <span className="font-mono text-xs text-amber-400 uppercase tracking-wider">Module 04 / changelog_gen</span>
              <h3 className="text-xl font-bold text-white mt-1 mb-3">Conventional Changelogs</h3>
              <p className="text-sm text-neutral-300 leading-relaxed mb-6">
                Parses <code className="text-neutral-300">git log</code> commits, groups by prefix (<code className="text-neutral-300">feat</code> / <code className="text-neutral-300">fix</code> / <code className="text-neutral-300">breaking</code>), and dispatches viaSocket release payloads.
              </p>
            </div>
            <div className="pt-6 border-t border-[#1f1f1f] flex items-center justify-between">
              <span className="font-mono text-xs text-neutral-400">Event: changelog.generated</span>
              <button
                onClick={() => handleLaunchDemoJob('changelog_generator', { repo_url: 'https://github.com/shipfaster-ai/fastapi-template', commit_range: 'v1.4.0...v1.5.0' })}
                disabled={demoLoading !== null}
                className="px-3.5 py-2 rounded-xl bg-[#1f1f1f] hover:bg-amber-500 text-xs font-semibold text-white transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                Build Changelog
              </button>
            </div>
          </div>

          {/* Module 5: Notebook to Blog (Human-in-Loop Gate Spotlight) */}
          <div className="md:col-span-4 glass-panel rounded-2xl p-8 border border-[#00f0ff]/40 bg-gradient-to-b from-[#141414] to-[#0a0a0a] shadow-[0_0_30px_rgba(0,240,255,0.06)] flex flex-col justify-between group">
            <div>
              <div className="w-12 h-12 rounded-xl bg-pink-500/10 border border-pink-500/30 flex items-center justify-center mb-6 text-pink-400">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-xs text-pink-400 uppercase tracking-wider">Module 05 / nb_to_blog</span>
                <span className="px-2 py-0.5 rounded bg-[#00f0ff]/15 text-[#00f0ff] font-mono text-[10px] uppercase font-semibold">Human Gate</span>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Notebook to Social Draft</h3>
              <p className="text-sm text-neutral-300 leading-relaxed mb-6">
                Converts <code className="text-neutral-300">nbformat</code> Jupyter notebooks into technical blog drafts, uploads embedded cell images to S3, and awaits explicit reviewer approval before viaSocket dispatch.
              </p>
            </div>
            <div className="pt-6 border-t border-[#1f1f1f] flex items-center justify-between">
              <span className="font-mono text-xs text-neutral-400">Hook: viaSocket LinkedIn</span>
              <button
                onClick={() => handleLaunchDemoJob('notebook_to_blog', { notebook_path: 's3://shipfaster-inputs/churn_analysis.ipynb', target_platform: 'linkedin_and_twitter' })}
                disabled={demoLoading !== null}
                className="px-3.5 py-2 rounded-xl bg-[#00f0ff] hover:bg-[#00d0df] text-[#0a0a0a] text-xs font-bold transition-all flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Launch Gate Demo
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
