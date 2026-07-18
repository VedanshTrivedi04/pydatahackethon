import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Terminal, ShieldCheck, Key, Cpu, Sparkles, Layers } from 'lucide-react';
import { getTenantApiKey, setTenantApiKey, getTenantId, setTenantId } from '../../api/client';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [showConfig, setShowConfig] = useState(false);
  const [apiKey, setApiKey] = useState(getTenantApiKey());
  const [tenantId, setTenantState] = useState(getTenantId());
  const [toast, setToast] = useState<string | null>(null);

  const handleSaveConfig = (e: React.FormEvent) => {
    e.preventDefault();
    setTenantApiKey(apiKey);
    setTenantId(tenantId);
    setShowConfig(false);
    setToast('Authentication credentials updated successfully');
    setTimeout(() => setToast(null), 3000);
  };

  const isActive = (path: string) => {
    if (path === '/' && location.pathname !== '/') return false;
    return location.pathname.startsWith(path);
  };

  return (
    <>
      <header className="glass-header sticky top-0 z-50 h-20 px-6 lg:px-12 flex items-center justify-between transition-all">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00f0ff] to-[#0080ff] flex items-center justify-center shadow-[0_0_15px_rgba(0,240,255,0.3)] transition-transform group-hover:scale-105">
              <Cpu className="w-5 h-5 text-[#0a0a0a]" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
                ShipFaster <span className="text-[#00f0ff] text-xs px-1.5 py-0.5 rounded bg-[#00f0ff]/10 border border-[#00f0ff]/30 font-normal">v1.5</span>
              </span>
              <span className="text-[11px] text-neutral-400 font-mono -mt-1 tracking-wider uppercase">Agent Orchestrator</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 bg-[#141414] p-1 rounded-xl border border-[#1f1f1f]">
            <Link
              to="/"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive('/') && location.pathname === '/'
                  ? 'bg-[#1f1f1f] text-[#00f0ff] shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[#1a1a1a]'
              }`}
            >
              Overview
            </Link>
            <Link
              to="/dashboard"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                isActive('/dashboard') || isActive('/jobs')
                  ? 'bg-[#1f1f1f] text-[#00f0ff] shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[#1a1a1a]'
              }`}
            >
              <Terminal className="w-4 h-4" />
              Jobs Monitor
            </Link>
            <Link
              to="/preview"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                isActive('/preview')
                  ? 'bg-[#1f1f1f] text-[#00f0ff] shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[#1a1a1a]'
              }`}
            >
              <Layers className="w-4 h-4" />
              Docs Hub
            </Link>
          </nav>
        </div>

        {/* Status Indicators & Auth Settings */}
        <div className="flex items-center gap-4">
          <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#141414] border border-[#1f1f1f] text-xs text-neutral-300">
            <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-pulse"></span>
            <span className="font-mono">viaSocket: Connected</span>
          </div>

          <button
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#141414] hover:bg-[#1f1f1f] border border-[#1f1f1f] hover:border-[#00f0ff]/40 text-xs font-mono text-neutral-300 hover:text-white transition-all shadow-sm"
          >
            <Key className="w-3.5 h-3.5 text-[#00f0ff]" />
            <span>{tenantId}</span>
          </button>
        </div>
      </header>

      {/* Auth & Tenant Config Popover/Modal */}
      {showConfig && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 border border-[#00f0ff]/30 shadow-[0_0_40px_rgba(0,240,255,0.1)]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-[#00f0ff]" />
                Tenant & Authentication Setup
              </h3>
              <button
                onClick={() => setShowConfig(false)}
                className="text-neutral-400 hover:text-white text-sm px-2 py-1"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-neutral-400 mb-6 leading-relaxed">
              Every request attaches <code className="text-[#00f0ff] bg-[#1a1a1a] px-1.5 py-0.5 rounded">Authorization: Bearer &lt;key&gt;</code> to Dev 3's OpenAPI endpoints and isolates outputs to the current tenant ID.
            </p>

            <form onSubmit={handleSaveConfig} className="space-y-4 font-mono text-sm">
              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-400 mb-1.5">Tenant ID</label>
                <input
                  type="text"
                  value={tenantId}
                  onChange={(e) => setTenantState(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-[#1f1f1f] focus:border-[#00f0ff] rounded-xl px-3.5 py-2.5 text-white outline-none transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-400 mb-1.5">Tenant API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-[#1f1f1f] focus:border-[#00f0ff] rounded-xl px-3.5 py-2.5 text-white outline-none transition-colors"
                  required
                />
              </div>

              <div className="pt-2 flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowConfig(false)}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-[#1f1f1f] text-neutral-300 hover:text-white text-xs font-sans font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 rounded-xl bg-[#00f0ff] hover:bg-[#00d0df] text-[#0a0a0a] text-xs font-sans font-bold transition-all shadow-[0_0_15px_rgba(0,240,255,0.3)]"
                >
                  Save Credentials
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Global Success Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-[#0f0f0f] border border-[#00f0ff] text-white text-sm font-medium flex items-center gap-3 shadow-[0_0_20px_rgba(0,240,255,0.25)] animate-bounce">
          <Sparkles className="w-4 h-4 text-[#00f0ff]" />
          <span>{toast}</span>
        </div>
      )}
    </>
  );
};
