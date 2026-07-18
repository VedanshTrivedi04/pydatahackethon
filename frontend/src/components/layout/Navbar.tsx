import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Terminal, ShieldCheck, Key, Cpu, Sparkles, Layers, LogOut, ArrowRight, UserPlus, Info } from 'lucide-react';
import { getTenantApiKey, setTenantApiKey, getTenantId, setTenantId, tenantsApi, authApi } from '../../api/client';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [showConfig, setShowConfig] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authTab, setAuthTab] = useState<'login' | 'signup' | 'demo'>('login');
  
  // Login input states (JWT Email & Password)
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  
  // Signup input states (JWT Registration)
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupWorkspaceName, setSignupWorkspaceName] = useState('');
  
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

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) {
      setAuthError('Please enter both Email and Password.');
      return;
    }
    setLoading(true);
    setAuthError(null);
    try {
      const res = await authApi.login(loginEmail, loginPassword);
      if (res && res.access_token) {
        localStorage.setItem('shipfaster_is_logged_in', 'true');
        setTenantApiKey(res.access_token);
        if (res.tenant_id) {
          setTenantId(res.tenant_id);
          setTenantState(res.tenant_id);
        }
        setShowAuthModal(false);
        window.location.href = '/';
      } else {
        throw new Error('Authentication failed');
      }
    } catch (err: any) {
      setAuthError(err.message || 'Incorrect email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signupEmail || !signupPassword || !signupName || !signupWorkspaceName) {
      setAuthError('Please fill in all registration fields.');
      return;
    }
    setAuthError(null);
    setLoading(true);
    try {
      const res = await authApi.register(signupEmail, signupPassword, signupName, signupWorkspaceName);
      if (res && res.access_token) {
        localStorage.setItem('shipfaster_is_logged_in', 'true');
        setTenantApiKey(res.access_token);
        if (res.tenant_id) {
          setTenantId(res.tenant_id);
          setTenantState(res.tenant_id);
        }
        setShowAuthModal(false);
        window.location.href = '/';
      } else {
        throw new Error('Invalid response from backend');
      }
    } catch (err: any) {
      setAuthError(err.message || 'Tenant registration failed. Make sure email is valid and workspace name is unique.');
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
      <header className="glass-header sticky top-0 z-50 h-20 px-6 lg:px-12 flex items-center justify-between transition-all border-b border-[#1f1f1f] bg-black/40 backdrop-blur-md">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00f0ff] to-[#7c3aed] flex items-center justify-center shadow-[0_0_15px_rgba(0,240,255,0.25)] transition-transform group-hover:scale-105">
              <Cpu className="w-5 h-5 text-black animate-pulse" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
                ShipFaster <span className="text-[#00f0ff] text-xs px-1.5 py-0.5 rounded bg-[#00f0ff]/10 border border-[#00f0ff]/30 font-normal font-mono">v1.5</span>
              </span>
              <span className="text-[11px] text-neutral-400 font-mono -mt-1 tracking-wider uppercase">Agent Orchestrator</span>
            </div>
          </Link>

          {/* Navigation Links - Visible only if logged in */}
          {isLoggedIn && (
            <nav className="hidden md:flex items-center gap-1 bg-[#141414] p-1 rounded-xl border border-[#1f1f1f]">
              <Link
                to="/"
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive('/') && location.pathname === '/'
                    ? 'bg-[#242424] text-[#00f0ff] shadow-sm'
                    : 'text-neutral-400 hover:text-white hover:bg-[#1a1a1a]'
                }`}
              >
                Overview
              </Link>
              <Link
                to="/dashboard"
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  isActive('/dashboard') || isActive('/jobs')
                    ? 'bg-[#242424] text-[#00f0ff] shadow-sm'
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
                    ? 'bg-[#242424] text-[#00f0ff] shadow-sm'
                    : 'text-neutral-400 hover:text-white hover:bg-[#1a1a1a]'
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
              <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#141414] border border-[#1f1f1f] text-xs text-neutral-300">
                <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-pulse"></span>
                <span className="font-mono">viaSocket: Connected</span>
              </div>

              <button
                onClick={() => setShowConfig(!showConfig)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#141414] hover:bg-[#1f1f1f] border border-[#1f1f1f] hover:border-[#00f0ff]/45 text-xs font-mono text-neutral-300 hover:text-white transition-all shadow-sm"
              >
                <Key className="w-3.5 h-3.5 text-[#00f0ff]" />
                <span className="truncate max-w-[120px]">{tenantId}</span>
              </button>

              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-950/20 hover:bg-red-900/30 border border-red-500/20 hover:border-red-500/50 text-xs font-semibold text-red-400 hover:text-red-200 transition-all shadow-sm"
                title="Logout from Workspace"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
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
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#7c3aed] hover:from-[#00d0df] hover:to-[#6c2ade] text-black text-xs font-bold tracking-wide transition-all shadow-[0_0_20px_rgba(0,240,255,0.25)] flex items-center gap-2"
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
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 border border-[#00f0ff]/30 shadow-[0_0_40px_rgba(0,240,255,0.1)]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-[#00f0ff]" />
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
              Your active tenant space: <code className="text-[#00f0ff] bg-[#1a1a1a] px-1.5 py-0.5 rounded">{tenantId}</code>
            </p>

            <form onSubmit={handleSaveConfig} className="space-y-4 font-mono text-sm">
              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-400 mb-1.5 font-bold">Tenant ID / JWT Auth</label>
                <textarea
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  rows={4}
                  className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] rounded-xl px-3.5 py-2.5 text-white outline-none transition-colors font-mono text-[10px] resize-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-neutral-400 mb-1.5 font-bold">Active Tenant ID</label>
                <input
                  type="text"
                  value={tenantId}
                  onChange={(e) => setTenantState(e.target.value)}
                  className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] rounded-xl px-3.5 py-2.5 text-white outline-none transition-colors"
                  required
                />
              </div>

              <div className="pt-2 flex flex-col gap-2 font-sans">
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowConfig(false)}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-neutral-900 text-neutral-300 hover:text-white text-xs font-semibold transition-colors border border-neutral-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#7c3aed] text-black text-xs font-bold transition-all shadow-md"
                  >
                    Save Changes
                  </button>
                </div>
                
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full mt-2 px-4 py-2.5 rounded-xl bg-transparent hover:bg-red-950/20 border border-red-500/30 hover:border-red-500/50 text-red-400 text-xs font-semibold transition-all flex items-center justify-center gap-2"
                >
                  <LogOut className="w-4 h-4" />
                  Logout from Space
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Guest Authentication Modal */}
      {showAuthModal && !isLoggedIn && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-8 border border-neutral-800 shadow-[0_0_50px_rgba(0,240,255,0.08)] bg-[#050505]/95">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-xl font-bold text-white flex items-center gap-2.5 font-sans tracking-tight">
                <ShieldCheck className="w-5 h-5 text-[#00f0ff]" />
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
                  authTab === 'login' ? 'bg-[#00f0ff] text-black shadow-md' : 'text-neutral-500 hover:text-white'
                }`}
              >
                Login (JWT)
              </button>
              <button
                onClick={() => { setAuthTab('signup'); setAuthError(null); }}
                className={`flex-1 py-3 text-center transition-all duration-200 rounded-xl font-bold ${
                  authTab === 'signup' ? 'bg-[#00f0ff] text-black shadow-md' : 'text-neutral-500 hover:text-white'
                }`}
              >
                Create Private Space
              </button>
              <button
                onClick={() => { setAuthTab('demo'); setAuthError(null); }}
                className={`flex-1 py-3 text-center transition-all duration-200 rounded-xl font-bold ${
                  authTab === 'demo' ? 'bg-[#00f0ff] text-black shadow-md' : 'text-neutral-500 hover:text-white'
                }`}
              >
                Demo Space
              </button>
            </div>

            {authError && (
              <div className="p-4 mb-6 rounded-xl bg-red-950/20 border border-red-500/30 text-red-400 text-xs font-mono flex items-start gap-2.5">
                <Info className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{authError}</span>
              </div>
            )}

            {/* Login Form */}
            {authTab === 'login' && (
              <form onSubmit={handleLoginSubmit} className="space-y-5 font-mono text-xs">
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Email Address</label>
                  <input
                    type="email"
                    placeholder="e.g. dev@example.com"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value.trim())}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Account Password</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value.trim())}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 mt-6 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#7c3aed] text-black font-bold text-xs tracking-wider uppercase transition-all shadow-md flex items-center justify-center gap-2 active:scale-[0.98] disabled:opacity-50"
                >
                  {loading ? 'Authenticating...' : 'Sign In'} <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            )}

            {/* Signup/Register Form */}
            {authTab === 'signup' && (
              <form onSubmit={handleSignUpSubmit} className="space-y-5 font-mono text-xs">
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Developer / Full Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Vedansh Trivedi"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Email Address</label>
                  <input
                    type="email"
                    placeholder="e.g. dev@example.com"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value.trim())}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Password</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value.trim())}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] tracking-widest text-neutral-450 uppercase font-semibold mb-2">Workspace Name</label>
                  <input
                    type="text"
                    placeholder="e.g. My Workspace"
                    value={signupWorkspaceName}
                    onChange={(e) => setSignupWorkspaceName(e.target.value)}
                    className="w-full bg-[#000000] border border-neutral-850 focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] rounded-xl px-4 py-3.5 text-white outline-none transition-all placeholder-neutral-700 hover:border-neutral-800"
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 mt-6 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#7c3aed] text-black font-bold text-xs tracking-wider uppercase transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50 active:scale-[0.98]"
                >
                  {loading ? 'Creating Private Space...' : 'Register Workspace'} <UserPlus className="w-4 h-4" />
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
                  className="w-full py-4 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#7c3aed] text-black font-bold text-xs tracking-wider uppercase transition-all shadow-md flex items-center justify-center gap-2 active:scale-[0.98]"
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
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-[#0a0a0a] border border-[#00f0ff] text-white text-sm font-medium flex items-center gap-3 shadow-[0_0_20px_rgba(0,240,255,0.2)] animate-bounce">
          <Sparkles className="w-4 h-4 text-[#00f0ff] animate-pulse" />
          <span>{toast}</span>
        </div>
      )}
    </>
  );
};
