import React, { useState } from 'react';
import { jobsApi } from '../../api/client';
import { CheckCircle2, XCircle, Send, MessageSquare, Loader2, Sparkles } from 'lucide-react';

interface ApproveRejectPanelProps {
  jobId: string;
  isApproved?: boolean;
  isRejected?: boolean;
  initialFeedback?: string;
  onActionCompleted?: () => void;
}

export const ApproveRejectPanel: React.FC<ApproveRejectPanelProps> = ({
  jobId,
  isApproved,
  isRejected,
  initialFeedback,
  onActionCompleted,
}) => {
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);
  const [feedbackText, setFeedbackText] = useState(initialFeedback || '');
  const [loading, setLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState<'approved' | 'rejected' | null>(
    isApproved ? 'approved' : isRejected ? 'rejected' : null
  );
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const handleApprove = async () => {
    setLoading(true);
    try {
      await jobsApi.approveJob(jobId);
      setActionStatus('approved');
      setToastMessage('Approved! Publishing viaSocket payload to LinkedIn/X right now.');
      if (onActionCompleted) onActionCompleted();
    } catch (err: any) {
      alert(`Error approving draft: ${err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!showFeedbackInput && !feedbackText.trim()) {
      setShowFeedbackInput(true);
      return;
    }

    setLoading(true);
    try {
      await jobsApi.rejectJob(jobId, feedbackText);
      setActionStatus('rejected');
      setToastMessage('Rejected. Feedback dispatched to Dev 1 LLM module queue.');
      setShowFeedbackInput(false);
      if (onActionCompleted) onActionCompleted();
    } catch (err: any) {
      alert(`Error rejecting draft: ${err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-[#00f0ff]/30 shadow-[0_0_30px_rgba(0,240,255,0.06)] relative overflow-hidden my-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#00f0ff]/10 border border-[#00f0ff]/30 text-[#00f0ff] font-mono text-[11px] uppercase tracking-wider mb-2">
            <Sparkles className="w-3 h-3" /> Human-in-the-Loop Gate
          </div>
          <h3 className="text-lg font-bold text-white tracking-tight">
            Review Notebook-to-Blog Draft
          </h3>
          <p className="text-xs text-neutral-400 mt-1">
            This draft has been parsed from the Jupyter notebook and split into markdown cells and S3 image assets. Approving triggers Dev 3's viaSocket webhook directly to social channels.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 shrink-0">
          {actionStatus === 'approved' ? (
            <div className="px-4 py-2.5 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-semibold text-xs flex items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Approved & Published
            </div>
          ) : actionStatus === 'rejected' ? (
            <div className="px-4 py-2.5 rounded-xl bg-red-950/80 border border-red-500/40 text-red-300 font-semibold text-xs flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-400" />
              Rejected with Feedback
            </div>
          ) : (
            <>
              <button
                onClick={() => setShowFeedbackInput(!showFeedbackInput)}
                disabled={loading}
                className="px-4 py-2.5 rounded-xl bg-[#1a1a1a] hover:bg-[#242424] border border-[#2f2f2f] text-neutral-300 hover:text-white text-xs font-semibold transition-all flex items-center gap-2 disabled:opacity-50"
              >
                <MessageSquare className="w-3.5 h-3.5 text-amber-400" />
                Reject & Request Changes
              </button>

              <button
                onClick={handleApprove}
                disabled={loading}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#00f0ff] to-[#00b0ff] hover:opacity-90 text-[#0a0a0a] text-xs font-bold transition-all shadow-[0_0_20px_rgba(0,240,255,0.3)] flex items-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin text-[#0a0a0a]" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-[#0a0a0a]" />
                )}
                Approve & Publish viaSocket
              </button>
            </>
          )}
        </div>
      </div>

      {/* Rejection Feedback Box */}
      {(showFeedbackInput || actionStatus === 'rejected') && (
        <div className="mt-4 pt-4 border-t border-[#1f1f1f] transition-all">
          <label className="block text-xs font-mono text-neutral-400 mb-2">
            {actionStatus === 'rejected' ? 'Submitted Rejection Feedback:' : 'Explain necessary adjustments for Dev 1 LLM Module:'}
          </label>
          {actionStatus === 'rejected' ? (
            <div className="p-3.5 rounded-xl bg-[#0a0a0a] border border-red-500/30 text-red-200 text-xs font-mono">
              {feedbackText || 'No specific feedback provided.'}
            </div>
          ) : (
            <div className="flex gap-2">
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="e.g. Ensure the SHAP formula explanation is included before code block 2..."
                rows={2}
                className="flex-1 bg-[#0a0a0a] border border-[#242424] focus:border-red-400 rounded-xl p-3 text-white text-xs font-mono outline-none resize-none transition-colors"
              />
              <button
                onClick={handleReject}
                disabled={loading || !feedbackText.trim()}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs flex items-center gap-2 self-end disabled:opacity-50 transition-all shadow-[0_0_15px_rgba(239,68,68,0.3)]"
              >
                <Send className="w-3.5 h-3.5" />
                Submit Rejection
              </button>
            </div>
          )}
        </div>
      )}

      {/* Notification Banner */}
      {toastMessage && (
        <div className="mt-4 p-3 rounded-xl bg-[#0a0a0a] border border-[#00f0ff]/50 text-[#00f0ff] font-mono text-xs flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
};
