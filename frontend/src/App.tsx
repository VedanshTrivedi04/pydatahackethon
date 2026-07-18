import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Landing } from './pages/Landing';
import { Overview } from './pages/Overview';
import { Dashboard } from './pages/Dashboard';
import { JobDetail } from './pages/JobDetail';
import { DocsPreview } from './pages/DocsPreview';

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
        <footer className="border-t border-[#1f1f1f] bg-[#0a0a0a] py-12 px-6 text-center font-mono text-xs text-neutral-500 relative z-10">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="text-left">
              <span className="text-white font-bold tracking-tight">ShipFaster Agentic Platform</span>
              <p className="text-neutral-600 mt-1">Multi-tenant Sandboxed Developer Automation Core</p>
            </div>
            <div className="flex items-center gap-6 text-neutral-600">
              <a href="#features" className="hover:text-white transition-colors">Features</a>
              <a href="#modules" className="hover:text-white transition-colors text-[#00f0ff]">Modules API</a>
              <span className="text-neutral-800">|</span>
              <span>© 2026 PyData Hackathon Project</span>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
};

export default App;
