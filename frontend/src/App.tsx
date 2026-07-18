import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Landing } from './pages/Landing';
import { Dashboard } from './pages/Dashboard';
import { JobDetail } from './pages/JobDetail';
import { DocsPreview } from './pages/DocsPreview';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-[#0a0a0a] text-[#faf9f6]">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/jobs" element={<Dashboard />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
          <Route path="/preview" element={<DocsPreview />} />
        </Routes>
      </main>
      <footer className="border-t border-[#1f1f1f] py-8 px-6 text-center font-mono text-xs text-neutral-500">
        ShipFaster • PyData Hackathon Track: Unified Developer Automation & viaSocket Integration
      </footer>
    </div>
  );
};

export default App;
