import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Terminal, ShieldCheck, Key, Cpu, Sparkles, Layers, LogOut, ArrowRight, UserPlus, Info } from 'lucide-react';
import { getTenantApiKey, setTenantApiKey, getTenantId, setTenantId, tenantsApi } from '../../api/client';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [showConfig, setShowConfig] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authTab, setAuthTab] = useState<'login' | 'signup' | 'demo'>('login');
  
  // Login input states
  const [loginTenantId, setLoginTenantId] = useState('');
  const [loginApiKey, setLoginApiKey] = useState('');
  
  // Signup input states
  const [signupName, setSignupName] = useState('');
  const [signupSlug, setSignupSlug] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  
  const [apiKey, setApiKey] = useState(getTenantApiKey());
  const [tenantId, setTenantState] = useState(getTenantId());
  const [toast, setToast] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isLoggedIn = localStorage.getItem('shipfaster_is_logged_in') === 'true';

  React.useEffect(() => {
    const handleOpenAuth = () => {
      setAuthError(null);
      setAuthTab('login');
      setShowAuthModal(true);
    };
    window.addEventListener('open-auth-modal', handleOpenAuth);
    return () => window.removeEventListener('open-auth-modal', handleOpenAuth);
  }, []);

  const handleSaveConfig = (e: React.FormEvent) => {
    e.preventDefault();
    setTenantApiKey(apiKey);
    setTenantId(tenantId);
    setShowConfig(false);
    setToast('Authentication credentials updated successfully');
    setTimeout(() => setToast(null), 3000);
  };

  const handleLogout = () => {
    localStorage.setItem('shipfaster_is_logged_in', 'false');
    localStorage.removeItem('shipfaster_api_key');
    localStorage.removeItem('shipfaster_tenant_id');
    window.location.href = '/';
  };

  const handleDemoLogin = () => {
    localStorage.setItem('shipfaster_is_logged_in', 'true');
    // Save live demo credentials
    setTenantApiKey('sf_2314922a84f1f04209f3040f302bed7d98e545b4350850c1dd4455c809b1387b');
    setTenantId('d3c89532-fa95-4e6b-a5d1-cbdb6628039e');
    setShowAuthModal(false);
    window.location.href = '/';
  };

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginTenantId || !loginApiKey) {
      setAuthError('Please enter both Tenant ID and API Key.');
      return;
    }
    localStorage.setItem('shipfaster_is_logged_in', 'true');
    setTenantApiKey(loginApiKey);
    setTenantId(loginTenantId);
    setShowAuthModal(false);
    window.location.href = '/';
  };

  const handleSignUpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setLoading(true);
    try {
      const res = await tenantsApi.createTenant(signupName, signupSlug, signupEmail);
      if (res && res.tenant && res.api_key) {
        localStorage.setItem('shipfaster_is_logged_in', 'true');
        setTenantApiKey(res.api_key);
        setTenantId(res.tenant.id);
        setShowAuthModal(false);
        window.location.href = '/';
      } else {
        throw new Error('Invalid response from backend');
      }
    } catch (err: any) {
      setAuthError(err.message || 'Tenant registration failed. Make sure the slug is unique and alphanumeric.');
    } finally {
      setLoading(false);
    }
  };

  const isActive = (path: string) => {
    if (path === '/' && location.pathname !== '/') return false;
    return location.pathname.startsWith(path);
  };

  return (
    <>
      <header className="glass-header sticky top-0 z-50 h-20 px-6 lg:px-12 flex items-center justify-between transition-all border-b border-neutral-900 bg-black/40 backdrop-blur-md">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-[0_0_15px_rgba(255,255,255,0.15)] transition-transform group-hover:scale-105">
              <Cpu className="w-5 h-5 text-black" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
                ShipFaster <span className="text-white text-xs px-1.5 py-0.5 rounded bg-neutral-900 border border-neutral-800 font-normal">v1.5</span>
              </span>
              <span className="text-[11px] text-neutral-500 font-mono -mt-1 tracking-wider uppercase">Agent Orchestrator</span>
            </div>
          </Link>

          {/* Navigation Links - Visible only if logged in */}
          {isLoggedIn && (
            <nav className="hidden md:flex items-center gap-1 bg-[#0d0d0d] p-1 rounded-xl border border-neutral-850">
              <Link
                to="/"
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive('/') && location.pathname === '/'
                    ? 'bg-white text-black shadow-sm'
                    : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
                }`}
              >
                Overview
              </Link>
              <Link
                to="/dashboard"
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  isActive('/dashboard') || isActive('/jobs')
                    ? 'bg-white text-black shadow-sm'
                    : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
                }`}
              >
                <Terminal className="w-4 h-4" />
                Jobs Monitor
              </Link>
              <Link
                to="/preview"
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  isActive('/preview')
                    ? 'bg-white text-black shadow-sm'
                    : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
                }`}
              >
                <Layers className="w-4 h-4" />
                Docs Hub
              </Link>
            </nav>
          )}
        </div>

        {/* Status Indicators & Auth Settings */}
        <div className="flex items-center gap-4">
          {isLoggedIn ? (
            <>
              {/* Connected indicators - Visible only if logged in */}
              <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0d0d0d] border border-neutral-850 text-xs text-neutral-300">
                <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                <span className="font-mono">viaSocket: Connected</span>
              </div>

              <button
                onClick={() => setShowConfig(!showConfig)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#0d0d0d] hover:bg-neutral-900 border border-neutral-850 hover:border-neutral-700 text-xs font-mono text-neutral-300 hover:text-white transition-all shadow-sm"
              >
                <Key className="w-3.5 h-3.5 text-white" />
                <span className="truncate max-w-[120px]">{tenantId}</span>
              </button>
            </>
          ) : (
            /* Login button - Visible only when NOT logged in */
            <button
              onClick={() => {
                setAuthError(null);
                setAuthTab('login');
                setShowAuthModal(true);
              }}
              className="px-5 py-2.5 rounded-xl bg-white hover:bg-neutral-200 text-black text-xs font-bold tracking-wide transition-all shadow-[0_0_15px_rgba(255,255,255,0.15)] flex items-center gap-2"
            >
              <ShieldCheck className="w-4 h-4" />
              Sign Up / Login
            </button>
          )}
        </div>
      </header>

      {/* Credentials Setup Popover (for logged in tenants) */}
      {showConfig && isLoggedIn && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 border border-neutral-800 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-white" />
                Workspace Credentials
              </h3>
              <button
                onClick={() => setShowConfig(false)}
                className="text-neutral-400 hover:text-white text-sm px-2 py-1"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-neutral-400 mb-6 leading-relaxed font-mono">
              Your active tenant space: <code className="text-white bg-neutral-900 px-1.5 py-0.5 rounded">{tenantId}</code>
            </p>

            <form onSubmit={handleSaveConfig} className="space-y-4 font-mono text-sm">
              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-500 mb-1.5 font-bold">Tenant ID</label>
                <input
                  type="text"
                  value={tenantId}
                  onChange={(e) => setTenantState(e.target.value)}
                  className="w-full bg-[#000000] border border-neutral-850 focus:border-white rounded-xl px-3.5 py-2.5 text-white outline-none transition-colors"
                  required
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-500 mb-1.5 font-bold">Tenant API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full bg-[#000000] border border-neutral-850 focus:border-white rounded-xl px-3.5 py-2.5 text-white outline-none transition-colors"
                  required
                />
              </div>

              <div className="pt-2 flex flex-col gap-2 font-sans">
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowConfig(false)}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-neutral-900 text-neutral-300 hover:text-white text-xs font-semibold transition-colors border border-neutral-850"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2.5 rounded-xl bg-white hover:bg-neutral-200 text-black text-xs font-bold transition-all shadow-md"
                  >
                    Save Changes
                  </button>
                </div>
                
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full mt-2 px-4 py-2.5 rounded-xl bg-transparent hover:bg-neutral-950 border border-neutral-800 hover:border-neutral-700 text-neutral-300 text-xs font-semibold transition-all flex items-center justify-center gap-2"
                >
                  <LogOut className="w-4 h-4" />
                  Logout from Space
                </button>
              </div>
            </form>
          </div>
        </div>
      )}      {/* Guest Authentication Modal */}
      {showAuthModal && !isLoggedIn && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-8 border border-neutral-850 shadow-[0_0_50px_rgba(255,255,255,0.03)] bg-[#050505]/95 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-xl font-bold text-white flex items-center gap-2.5 font-sans tracking-tight">
                <ShieldCheck className="w-5 h-5 text-white" />
                Authenticate Workspace
              </h3>
              <button
                onClick={() => setShowAuthModal(false)}
                className="p-2 hover:bg-neutral-900 rounded-lg text-neutral-500 hover:text-white transition-all text-xs"
              >
                ✕
              </button>
            </div>

            {/* Modal Tabs: Segmented Control */}
            <div className="bg-[#0f0f0f] p-1.5 rounded-2xl flex gap-1.5 mb-8 border border-neutral-850 font-mono text-xs shadow-[inset_0_1px_3px_rgba(0,0,0,0.5)]">
              <button
                onClick={() => { setAuthTab('login'); setAuthError(null); }}
                className={`flex-1 py-3 text-center transition-all duration-200 rounded-xl font-bold ${
                  authTab === 'login' ? 'bg-white text-black shadow-md' : 'text-neutral-500 hover:text-white'
                }`}
              >
                Login (Credentials)
              </button>
              <button
                onClick={() => { setAuthTab('signup'); setAuthError(null); }}
                className={`flex-1 py-3 text-center transition-all duration-200 rounded-xl font-bold ${
                  authTab === 'signup' ? 'bg-white text-black shadow-md' : 'text-neutral-500 hover:text-white'
                }`}
              >
                Create Private Space
              </button>
              <button
                onClick={() => { setAuthTab('demo'); setAuthError(null); }}
                className={`flex-1 py-3 text-center transition-all duration-200 rounded-xl font-bold ${
                  authTab === 'demo' ? 'bg-white text-black shadow-md' : 'text-neutral-500 hover:text-white'
                }`}
              >
                Demo Space
              </button>
            </div>

            {authError && (
              <div className="p-4 mb-6 rounded-xl bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs font-mono flex items-start gap-2.5">
                <Info className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{authError}</span>
              </div>
            )}

            {/* Login Form */}
            {authTab === 'login' && (
              <form onSubmit={handleLoginSubmit} className="space-y-5 font-mono text-xs">
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-500 uppercase font-semibold mb-2">Tenant Space UUID</label>
                  <input
                    type="text"
                    placeholder="e.g. d3c89532-fa95-4e6b-a5d1-cbdb6628039e"
                    value={loginTenantId}
                    onChange={(e) => setLoginTenantId(e.target.value.trim())}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-white focus:ring-1 focus:ring-white rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-500 uppercase font-semibold mb-2">API Secret Key</label>
                  <input
                    type="password"
                    placeholder="Enter your tenant api key"
                    value={loginApiKey}
                    onChange={(e) => setLoginApiKey(e.target.value.trim())}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-white focus:ring-1 focus:ring-white rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-4 mt-6 rounded-xl bg-white hover:bg-neutral-200 text-black font-bold text-xs tracking-wider uppercase transition-all shadow-md flex items-center justify-center gap-2 active:scale-[0.98]"
                >
                  Connect Workspace <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            )}

            {/* Signup/Register Form */}
            {authTab === 'signup' && (
              <form onSubmit={handleSignUpSubmit} className="space-y-5 font-mono text-xs">
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-500 uppercase font-semibold mb-2">Developer / Org Name</label>
                  <input
                    type="text"
                    placeholder="e.g. My Workspace, Vedansh, Dev Team"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-white focus:ring-1 focus:ring-white rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-500 uppercase font-semibold mb-2">Workspace Slug (unique ID)</label>
                  <input
                    type="text"
                    placeholder="e.g. acme-workspace (lowercase, hyphens)"
                    value={signupSlug}
                    onChange={(e) => setSignupSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-white focus:ring-1 focus:ring-white rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-500 uppercase font-semibold mb-2">Contact Email (Optional)</label>
                  <input
                    type="email"
                    placeholder="e.g. dev@example.com"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-white focus:ring-1 focus:ring-white rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 mt-6 rounded-xl bg-white hover:bg-neutral-200 text-black font-bold text-xs tracking-wider uppercase transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50 active:scale-[0.98]"
                >
                  {loading ? 'Creating Private Schema...' : 'Register Workspace'} <UserPlus className="w-4 h-4" />
                </button>
              </form>
            )}

            {/* Quick Demo Option */}
            {authTab === 'demo' && (
              <div className="space-y-6 text-center font-sans">
                <p className="text-sm text-neutral-400 leading-relaxed max-w-sm mx-auto">
                  Instantly connect to our live demo tenant space database. Perfect for exploring the 5 LLM modules immediately!
                </p>
                <div className="p-4 rounded-xl bg-[#000000] border border-neutral-850 text-xs font-mono text-left space-y-2.5 text-neutral-500">
                  <div><span className="text-neutral-600 mr-2">Tenant:</span> d3c89532-fa95-4e6b-a5d1-cbdb6628039e</div>
                  <div><span className="text-neutral-600 mr-2">Secret:</span> sf_2314922a84f1... (Live Demo Key)</div>
                </div>
                <button
                  onClick={handleDemoLogin}
                  className="w-full py-4 rounded-xl bg-white hover:bg-neutral-200 text-black font-bold text-xs tracking-wider uppercase transition-all shadow-md flex items-center justify-center gap-2 active:scale-[0.98]"
                >
                  Use Live Demo Space <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Global Success Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-[#0a0a0a] border border-white text-white text-sm font-medium flex items-center gap-3 shadow-2xl animate-bounce">
          <Sparkles className="w-4 h-4 text-white animate-pulse" />
          <span>{toast}</span>
        </div>
      )}
    </>
  );
};
