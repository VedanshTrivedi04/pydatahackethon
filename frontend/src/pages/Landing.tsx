import React from 'react';
import { Terminal, Cpu, Box, Code2, FileText, GitCommit, FileSpreadsheet, Play, Sparkles, Zap, Shield, Database, ChevronRight, Info } from 'lucide-react';

export const Landing: React.FC = () => {
  const triggerAuthModal = () => {
    window.dispatchEvent(new Event('open-auth-modal'));
  };

  return (
    <div className="min-h-screen bg-[#030303] text-white overflow-hidden pb-12 relative">
      {/* Background Subtle Monochrome Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff03_1px,transparent_1px),linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#fff_60%,transparent_100%)] pointer-events-none" />

      {/* Hero Section */}
      <section className="relative pt-28 pb-16 px-6 lg:px-12 max-w-7xl mx-auto text-center z-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#121212] border border-[#00f0ff]/30 text-xs font-mono text-[#00f0ff] mb-8 shadow-[0_0_20px_rgba(0,240,255,0.1)]">
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span>PyData Hackathon: Multi-Tenant Agent Automation Platform</span>
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight max-w-4xl mx-auto leading-[1.1] mb-6 text-white">
          Ship Faster with <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#00f0ff] to-[#7c3aed]">Agentic Developer Automation.</span>
        </h1>

        <p className="text-base sm:text-lg text-neutral-400 max-w-2xl mx-auto leading-relaxed mb-10">
          Orchestrate 5 specialized LLM modules from CLI and MCP server, connected directly to viaSocket workflows in a secure, isolated multi-tenant environment.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={triggerAuthModal}
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#7c3aed] hover:from-[#00d0df] hover:to-[#6c2ade] text-black font-bold text-sm tracking-wide transition-all shadow-[0_0_25px_rgba(0,240,255,0.3)] flex items-center justify-center gap-2"
          >
            <Shield className="w-4 h-4" />
            Create Your Private Space
            <ChevronRight className="w-4 h-4" />
          </button>

          <a
            href="#features"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-transparent hover:bg-[#121212] border border-neutral-850 hover:border-neutral-700 text-neutral-200 font-semibold text-sm transition-all flex items-center justify-center gap-2"
          >
            <InfoIcon className="w-4 h-4 text-[#00f0ff]" />
            Learn More
          </a>
        </div>
      </section>

      {/* Main Centerpiece Image Mockup */}
      <section className="relative px-6 lg:px-12 max-w-5xl mx-auto pb-16 z-10">
        <div className="rounded-2xl overflow-hidden border border-neutral-850 shadow-2xl relative bg-[#0a0a0a]">
          <div className="absolute inset-0 bg-gradient-to-t from-[#030303] via-transparent to-transparent z-10 pointer-events-none" />
          <img
            src="/hero_automation.png"
            alt="Developer Automation & Agent Orchestration Flow Diagram"
            className="w-full h-auto object-cover max-h-[550px] opacity-90 filter grayscale contrast-125"
          />
        </div>
      </section>

      {/* Statistics Section */}
      <section className="relative px-6 lg:px-12 max-w-6xl mx-auto py-8 z-10">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 p-6 rounded-2xl bg-[#0a0a0a]/80 border border-neutral-850 backdrop-blur-md">
          <div className="text-center md:text-left">
            <span className="text-2xl sm:text-3xl font-extrabold text-white font-mono block">1,450+</span>
            <span className="text-xs text-neutral-500 font-mono mt-1 block">Active Developers</span>
          </div>
          <div className="text-center md:text-left border-l border-neutral-850 pl-0 md:pl-6">
            <span className="text-2xl sm:text-3xl font-extrabold text-[#00f0ff] font-mono block">98.4%</span>
            <span className="text-xs text-neutral-500 font-mono mt-1 block">Task Success Rate</span>
          </div>
          <div className="text-center md:text-left border-l border-neutral-850 pl-0 md:pl-6">
            <span className="text-2xl sm:text-3xl font-extrabold text-white font-mono block">35,000+</span>
            <span className="text-xs text-neutral-500 font-mono mt-1 block">Sandboxed Jobs Run</span>
          </div>
          <div className="text-center md:text-left border-l border-neutral-850 pl-0 md:pl-6">
            <span className="text-2xl sm:text-3xl font-extrabold text-emerald-400 font-mono block">0 ms</span>
            <span className="text-xs text-neutral-500 font-mono mt-1 block">Eager Fallback Latency</span>
          </div>
        </div>
      </section>

      {/* About Section with Schema Isolation Image */}
      <section id="features" className="relative px-6 lg:px-12 max-w-7xl mx-auto py-20 z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
          <div className="lg:col-span-6 space-y-6">
            <span className="font-mono text-xs text-[#00f0ff] uppercase tracking-widest block">
              Secure Architecture
            </span>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white leading-tight">
              Enterprise-Grade Multi-Tenant Isolation
            </h2>
            <p className="text-neutral-400 text-sm sm:text-base leading-relaxed">
              ShipFaster is engineered to provide complete developer isolation. Every organization registers their own Tenant Space, which creates a dedicated PostgreSQL schema sandbox. 
            </p>
            
            <div className="space-y-4 pt-2">
              <div className="flex gap-4">
                <div className="w-10 h-10 rounded-lg bg-[#00f0ff]/10 border border-[#00f0ff]/30 flex items-center justify-center text-[#00f0ff] shrink-0">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-white text-sm">Schema Sandboxing</h4>
                  <p className="text-xs text-neutral-500 mt-0.5">Your tasks, artifacts, and database logs are kept strictly separated. Cross-tenant data leaks are mathematically blocked at the database boundary.</p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-white text-sm">Automated Event Pipeline</h4>
                  <p className="text-xs text-neutral-500 mt-0.5">Upon task completion, Webhook integration directly dispatches release artifacts and documentation payloads to viaSocket workflows.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="rounded-2xl overflow-hidden border border-neutral-850 shadow-xl bg-[#0a0a0a]">
              <img
                src="/schema_isolation.png"
                alt="Multi-Tenant Database Isolation & Compartmentalized Container Architecture"
                className="w-full h-auto object-cover max-h-[380px] opacity-90 filter grayscale contrast-125"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section id="modules" className="relative px-6 lg:px-12 max-w-7xl mx-auto py-16 z-10 border-t border-neutral-900">
        <div className="mb-12 text-center lg:text-left">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-2">
            Automated Platform Modules
          </h2>
          <p className="text-sm text-neutral-500 font-mono">
            Create a space to run sandboxed developer automation tasks directly on our queue.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Module 1 */}
          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 flex flex-col justify-between hover:border-[#00f0ff]/40 transition-all bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#00f0ff]/10 border border-[#00f0ff]/30 flex items-center justify-center mb-4 text-[#00f0ff]">
                <Box className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">Project Scaffolder</h3>
              <p className="text-xs text-neutral-500 leading-relaxed mb-4">
                Generates complete multi-layered directories with FastAPI core, models, and Compose setup in isolated zip files.
              </p>
            </div>
            <button
              onClick={triggerAuthModal}
              className="mt-2 w-full py-2 rounded-xl bg-[#141414] hover:bg-[#00f0ff] hover:text-black text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Start Scaffolding Workspace
            </button>
          </div>

          {/* Module 2 */}
          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 flex flex-col justify-between hover:border-emerald-500/40 transition-all bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-4 text-emerald-400">
                <Code2 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">Pytest Suite Writer</h3>
              <p className="text-xs text-neutral-500 leading-relaxed mb-4">
                Scans async FastAPI handler routes and constructs robust unit test scripts with preconfigured fixtures.
              </p>
            </div>
            <button
              onClick={triggerAuthModal}
              className="mt-2 w-full py-2 rounded-xl bg-[#141414] hover:bg-emerald-500 hover:text-white text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Start Write Workspace
            </button>
          </div>

          {/* Module 3 */}
          <div className="glass-panel rounded-2xl p-6 border border-neutral-850 flex flex-col justify-between hover:border-violet-500/40 transition-all bg-[#0a0a0a] group">
            <div>
              <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center mb-4 text-violet-400">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">API Docs Generator</h3>
              <p className="text-xs text-neutral-500 leading-relaxed mb-4">
                Automatically builds clean OpenAPI YAML schemas and comprehensive implementation READMEs from routes.
              </p>
            </div>
            <button
              onClick={triggerAuthModal}
              className="mt-2 w-full py-2 rounded-xl bg-[#141414] hover:bg-violet-500 hover:text-white text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" /> Start Docs Workspace
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

const InfoIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
  </svg>
);
