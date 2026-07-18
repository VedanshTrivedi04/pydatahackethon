import React from 'react';
import { Link } from 'react-router-dom';
import { Job, ModuleType } from '../../api/types';
import { StatusBadge } from './StatusBadge';
import { Code2, FileText, GitCommit, FileSpreadsheet, Box, ArrowUpRight, Calendar } from 'lucide-react';

interface JobCardProps {
  job: Job;
}

export const JobCard: React.FC<JobCardProps> = ({ job }) => {
  const getModuleConfig = (module: ModuleType) => {
    switch (module) {
      case 'scaffolder':
        return {
          name: 'Project Scaffolder',
          icon: <Box className="w-4 h-4 text-[#00f0ff]" />,
          bg: 'bg-[#00f0ff]/10 border-[#00f0ff]/30',
        };
      case 'test_generator':
        return {
          name: 'Test Generator',
          icon: <Code2 className="w-4 h-4 text-emerald-400" />,
          bg: 'bg-emerald-500/10 border-emerald-500/30',
        };
      case 'docs_generator':
        return {
          name: 'Docs Generator',
          icon: <FileText className="w-4 h-4 text-violet-400" />,
          bg: 'bg-violet-500/10 border-violet-500/30',
        };
      case 'changelog_generator':
        return {
          name: 'Changelog Generator',
          icon: <GitCommit className="w-4 h-4 text-amber-400" />,
          bg: 'bg-amber-500/10 border-amber-500/30',
        };
      case 'notebook_to_blog':
        return {
          name: 'Notebook to Blog',
          icon: <FileSpreadsheet className="w-4 h-4 text-pink-400" />,
          bg: 'bg-pink-500/10 border-pink-500/30',
        };
      default:
        return {
          name: module,
          icon: <Box className="w-4 h-4 text-neutral-400" />,
          bg: 'bg-neutral-800 border-neutral-700',
        };
    }
  };

  const moduleConfig = getModuleConfig(job.module);

  // Extract a clean input summary from payload
  const getSummaryText = () => {
    if (job.payload.repo_url) {
      const repoName = job.payload.repo_url.split('/').slice(-2).join('/');
      if (job.payload.target_file) return `${repoName} → ${job.payload.target_file}`;
      if (job.payload.commit_range) return `${repoName} (${job.payload.commit_range})`;
      return `${repoName} [${job.payload.stack || 'full repo'}]`;
    }
    if (job.payload.notebook_path) {
      return job.payload.notebook_path.split('/').pop() || job.payload.notebook_path;
    }
    return JSON.stringify(job.payload).slice(0, 60);
  };

  const formattedDate = new Date(job.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <Link
      to={`/jobs/${job.job_id}`}
      className="group glass-panel rounded-2xl p-5 border border-[#1f1f1f] hover:border-[#00f0ff]/50 transition-all duration-200 hover:shadow-[0_4px_25px_rgba(0,240,255,0.08)] block relative overflow-hidden"
    >
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${moduleConfig.bg}`}>
            {moduleConfig.icon}
          </div>
          <div>
            <h4 className="font-semibold text-white text-sm group-hover:text-[#00f0ff] transition-colors flex items-center gap-1.5">
              {moduleConfig.name}
              <ArrowUpRight className="w-3.5 h-3.5 text-neutral-500 group-hover:text-[#00f0ff] opacity-0 group-hover:opacity-100 transition-all -translate-y-0.5 translate-x-0.5" />
            </h4>
            <span className="font-mono text-[11px] text-neutral-400">{job.job_id}</span>
          </div>
        </div>

        <StatusBadge status={job.status} size="sm" />
      </div>

      {/* Input Summary Box */}
      <div className="bg-[#0a0a0a] rounded-xl px-3.5 py-2.5 border border-[#1a1a1a] mb-3.5 font-mono text-xs text-neutral-300 truncate">
        <span className="text-neutral-500 mr-1.5">input:</span>
        {getSummaryText()}
      </div>

      <div className="flex items-center justify-between text-[11px] text-neutral-400 font-mono">
        <span className="flex items-center gap-1.5">
          <Calendar className="w-3 h-3 text-neutral-500" />
          {formattedDate}
        </span>
        <span className="px-2 py-0.5 rounded bg-[#1a1a1a] text-neutral-300 border border-[#242424]">
          {job.tenant_id}
        </span>
      </div>
    </Link>
  );
};
