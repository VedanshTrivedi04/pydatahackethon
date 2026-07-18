import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Landing } from './pages/Landing';
import { Overview } from './pages/Overview';
import { Dashboard } from './pages/Dashboard';
import { JobDetail } from './pages/JobDetail';
import { DocsPreview } from './pages/DocsPreview';
import { Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const isLoggedIn = localStorage.getItem('shipfaster_is_logged_in') === 'true';

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0a0a] text-[#faf9f6]">
      <Navbar />
      <main className="flex-1">
        <Routes>
          {/* Main Home Route: Shows Overview if logged in, otherwise Landing page */}
          <Route path="/" element={isLoggedIn ? <Overview /> : <Landing />} />

          {/* Protected Routes: redirect to / if not logged in */}
          <Route 
            path="/dashboard" 
            element={isLoggedIn ? <Dashboard /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/jobs" 
            element={isLoggedIn ? <Dashboard /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/jobs/:jobId" 
            element={isLoggedIn ? <JobDetail /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/preview" 
            element={isLoggedIn ? <DocsPreview /> : <Navigate to="/" replace />} 
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      
      {/* Global Landing Footer is displayed on the Landing page, or we can keep a unified tech footer */}
      {!isLoggedIn && (
        <footer className="border-t border-neutral-900 bg-[#000000] pt-16 pb-12 px-6 lg:px-12 relative z-10 font-sans text-xs text-neutral-500">
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-10 mb-12">
            {/* Brand Logo & Tagline */}
            <div className="md:col-span-4 space-y-4">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-white flex items-center justify-center shadow-md">
                  <Cpu className="w-3.5 h-3.5 text-black" />
                </div>
                <span className="font-mono font-bold text-sm tracking-tight text-white">
                  ShipFaster
                </span>
              </div>
              <p className="text-neutral-550 leading-relaxed max-w-sm">
                Multi-tenant sandboxed developer automation core. Orchestrate specialized LLM agents and pipelines securely.
              </p>
            </div>

            {/* Services Column */}
            <div className="md:col-span-3 space-y-3">
              <h4 className="font-mono text-[10px] uppercase tracking-widest text-neutral-400 font-bold">Services</h4>
              <ul className="space-y-2">
                <li><a href="#modules" className="hover:text-white transition-colors">Project Scaffolder</a></li>
                <li><a href="#modules" className="hover:text-white transition-colors">Pytest Suite Writer</a></li>
                <li><a href="#modules" className="hover:text-white transition-colors">API Docs Generator</a></li>
                <li><a href="#modules" className="hover:text-white transition-colors">Changelog Builder</a></li>
                <li><a href="#modules" className="hover:text-white transition-colors">Notebook to Social Draft</a></li>
              </ul>
            </div>

            {/* Security & Multi-Tenancy */}
            <div className="md:col-span-3 space-y-3">
              <h4 className="font-mono text-[10px] uppercase tracking-widest text-neutral-400 font-bold">Workspace Security</h4>
              <ul className="space-y-2">
                <li><span className="text-neutral-600">PostgreSQL Sandboxing</span></li>
                <li><span className="text-neutral-600">Isolated Tenant Schemas</span></li>
                <li><span className="text-neutral-600">Secure API Key Auth</span></li>
                <li><span className="text-neutral-600">Role-Based Access Control</span></li>
              </ul>
            </div>

            {/* Legal / Policies Column */}
            <div className="md:col-span-2 space-y-3">
              <h4 className="font-mono text-[10px] uppercase tracking-widest text-neutral-400 font-bold">Legal</h4>
              <ul className="space-y-2">
                <li><a href="#" onClick={(e) => { e.preventDefault(); alert("Privacy Policy: All codebase scans are performed in isolated RAM memory buffers and are never persisted or shared."); }} className="hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="#" onClick={(e) => { e.preventDefault(); alert("Terms of Service: By using ShipFaster, your tenant data is sandboxed under strict access control boundaries."); }} className="hover:text-white transition-colors">Terms of Service</a></li>
                <li><a href="#" onClick={(e) => { e.preventDefault(); alert("Cookie Settings: We only store session tokens in your local storage to maintain your connected workspace state."); }} className="hover:text-white transition-colors">Cookie Settings</a></li>
                <li><a href="#" onClick={(e) => { e.preventDefault(); alert("Security Disclosure: Cross-tenant data leaks are mathematically prevented by row-level and connection-level constraints."); }} className="hover:text-white transition-colors">Security Disclosure</a></li>
              </ul>
            </div>
          </div>

          {/* Bottom Row */}
          <div className="max-w-7xl mx-auto pt-8 border-t border-neutral-900 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-[10px] text-neutral-600">
            <span>© 2026 ShipFaster Agentic Platform. All rights reserved.</span>
            <div className="flex items-center gap-4">
              <span>PyData Hackathon Project</span>
              <span>•</span>
              <span className="text-neutral-500">Status: Operational</span>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
};

export default App;
