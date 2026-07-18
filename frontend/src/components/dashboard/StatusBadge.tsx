import React from 'react';
import { JobStatus } from '../../api/types';
import { CheckCircle2, Clock, Play, AlertTriangle, XCircle } from 'lucide-react';

interface StatusBadgeProps {
  status: JobStatus;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3.5 py-1.5 text-sm gap-2 font-semibold',
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  }[size];

  const config = {
    queued: {
      label: 'Queued',
      badgeClass: 'bg-neutral-800/80 text-neutral-300 border border-neutral-700/60',
      icon: <Clock className={`${iconSizes} text-neutral-400`} />,
    },
    running: {
      label: 'Running',
      badgeClass: 'bg-blue-950/70 text-blue-300 border border-blue-500/40 shadow-[0_0_12px_rgba(59,130,246,0.3)] animate-pulse',
      icon: <Play className={`${iconSizes} text-blue-400 fill-blue-400`} />,
    },
    success: {
      label: 'Success',
      badgeClass: 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.2)]',
      icon: <CheckCircle2 className={`${iconSizes} text-emerald-400`} />,
    },
    failed: {
      label: 'Failed',
      badgeClass: 'bg-red-950/80 text-red-300 border border-red-500/40 shadow-[0_0_12px_rgba(239,68,68,0.2)]',
      icon: <XCircle className={`${iconSizes} text-red-400`} />,
    },
    partial: {
      label: 'Partial Success',
      badgeClass: 'bg-amber-950/80 text-amber-300 border border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]',
      icon: <AlertTriangle className={`${iconSizes} text-amber-400`} />,
    },
  }[status] || {
    label: status,
    badgeClass: 'bg-neutral-800 text-neutral-300 border border-neutral-700',
    icon: <Clock className={iconSizes} />,
  };

  return (
    <span className={`inline-flex items-center rounded-lg font-mono font-medium transition-all ${sizeClasses} ${config.badgeClass}`}>
      {config.icon}
      <span>{config.label}</span>
    </span>
  );
};
