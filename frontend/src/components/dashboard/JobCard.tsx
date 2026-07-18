import React from 'react';
import { Link } from 'react-router-dom';
import { Job, ModuleType } from '../../api/types';
import { StatusBadge } from './StatusBadge';
import { Code2, FileText, GitCommit, FileSpreadsheet, Box, ArrowUpRight, Calendar, Trash2 } from 'lucide-react';

interface JobCardProps {
  job: Job;
  onDelete?: (e: React.MouseEvent) => void;
}

export const JobCard: React.FC<JobCardProps> = ({ job, onDelete }) => {
  const getModuleConfig = (module: ModuleType) => {
    switch (module) {
      case 'scaffolder':
        return {
          name: 'Project Scaffolder',
          icon: <Box className="w-4 h-4 text-white" />,
          bg: 'bg-[#121212] border-neutral-800',
        };
      case 'test_generator':
        return {
          name: 'Test Generator',
          icon: <Code2 className="w-4 h-4 text-white" />,
          bg: 'bg-[#121212] border-neutral-800',
        };
      case 'docs_generator':
        return {
          name: 'Docs Generator',
          icon: <FileText className="w-4 h-4 text-white" />,
          bg: 'bg-[#121212] border-neutral-800',
        };
      case 'changelog_generator':
        return {
          name: 'Changelog Generator',
          icon: <GitCommit className="w-4 h-4 text-white" />,
          bg: 'bg-[#121212] border-neutral-800',
        };
      case 'notebook_to_blog':
        return {
          name: 'Notebook to Blog',
          icon: <FileSpreadsheet className="w-4 h-4 text-white" />,
          bg: 'bg-[#121212] border-neutral-800',
        };
      default:
        return {
          name: module,
          icon: <Box className="w-4 h-4 text-neutral-400" />,
          bg: 'bg-neutral-900 border-neutral-800',
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
      className="group glass-panel rounded-2xl p-5 border border-neutral-850 hover:border-white transition-all duration-200 hover:shadow-[0_4px_25px_rgba(255,255,255,0.05)] block relative overflow-hidden bg-[#0a0a0a]"
    >
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${moduleConfig.bg}`}>
            {moduleConfig.icon}
          </div>
          <div>
            <h4 className="font-semibold text-white text-sm group-hover:underline transition-colors flex items-center gap-1.5">
              {moduleConfig.name}
              <ArrowUpRight className="w-3.5 h-3.5 text-neutral-500 opacity-0 group-hover:opacity-100 transition-all -translate-y-0.5 translate-x-0.5" />
            </h4>
            <span className="font-mono text-[11px] text-neutral-500">{job.job_id}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge status={job.status} size="sm" />
          {onDelete && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onDelete(e);
              }}
              className="p-1.5 rounded-lg hover:bg-neutral-900 text-neutral-500 hover:text-white transition-colors z-10"
              title="Delete Job"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Input Summary Box */}
      <div className="bg-[#000000] rounded-xl px-3.5 py-2.5 border border-neutral-850 mb-3.5 font-mono text-xs text-neutral-400 truncate">
        <span className="text-neutral-500 mr-1.5">input:</span>
        {getSummaryText()}
      </div>

      <div className="flex items-center justify-between text-[11px] text-neutral-500 font-mono">
        <span className="flex items-center gap-1.5">
          <Calendar className="w-3 h-3 text-neutral-600" />
          {formattedDate}
        </span>
        <span className="px-2 py-0.5 rounded bg-[#121212] text-neutral-400 border border-neutral-850">
          {job.tenant_id}
        </span>
      </div>
    </Link>
  );
};
