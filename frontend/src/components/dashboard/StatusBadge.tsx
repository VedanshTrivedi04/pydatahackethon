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
      badgeClass: 'bg-transparent text-neutral-500 border border-neutral-850',
      icon: <Clock className={`${iconSizes} text-neutral-500`} />,
    },
    running: {
      label: 'Running',
      badgeClass: 'bg-transparent text-white border border-white animate-pulse shadow-[0_0_15px_rgba(255,255,255,0.08)]',
      icon: <Play className={`${iconSizes} text-white fill-white`} />,
    },
    success: {
      label: 'Success',
      badgeClass: 'bg-white text-black border border-white font-bold',
      icon: <CheckCircle2 className={`${iconSizes} text-black fill-white`} />,
    },
    failed: {
      label: 'Failed',
      badgeClass: 'bg-transparent text-white border border-neutral-700',
      icon: <XCircle className={`${iconSizes} text-white`} />,
    },
    partial: {
      label: 'Partial Success',
      badgeClass: 'bg-transparent text-neutral-300 border border-neutral-700',
      icon: <AlertTriangle className={`${iconSizes} text-neutral-300`} />,
    },
  }[status] || {
    label: status,
    badgeClass: 'bg-transparent text-neutral-400 border border-neutral-800',
    icon: <Clock className={iconSizes} />,
  };

  return (
    <span className={`inline-flex items-center rounded-lg font-mono font-medium transition-all ${sizeClasses} ${config.badgeClass}`}>
      {config.icon}
      <span>{config.label}</span>
    </span>
  );
};
