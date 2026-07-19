import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { jobsApi } from '../api/client';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { ApproveRejectPanel } from '../components/dashboard/ApproveRejectPanel';
import { ArrowLeft, Download, Terminal, Code2, FileText, CheckCircle2, AlertCircle, Loader2, Copy, Check, ExternalLink } from 'lucide-react';
import { Highlight, themes } from 'prism-react-renderer';
import ReactMarkdown from 'react-markdown';

export const JobDetail: React.FC = () => {
  const { jobId = '' } = useParams<{ jobId: string }>();
  const [copied, setCopied] = useState(false);

  // Poll job detail every 2.5 seconds while status is queued or running
  const { data: job, isLoading, refetch } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'queued' || status === 'running' ? 2500 : false;
    },
  });

  const handleCopyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="min-h-[80vh] flex flex-col items-center justify-center text-center px-6">
        <Loader2 className="w-8 h-8 animate-spin text-[#00f0ff] mb-3" />
        <p className="font-mono text-sm text-neutral-400">Loading job detail {jobId} from Dev 3 API...</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="py-24 text-center px-6 max-w-md mx-auto">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-white mb-2">Job Not Found</h3>
        <p className="text-xs text-neutral-400 font-mono mb-6">We could not retrieve execution metrics for job {jobId}.</p>
        <Link to="/dashboard" className="px-4 py-2 rounded-xl bg-[#1f1f1f] text-white text-xs font-mono">
          ← Return to Dashboard
        </Link>
      </div>
    );
  }

  const isRunningOrQueued = job.status === 'queued' || job.status === 'running';

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white py-10 px-6 lg:px-12 max-w-6xl mx-auto">
      {/* Navigation Back */}
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-2 text-xs font-mono text-neutral-400 hover:text-[#00f0ff] transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Jobs Monitor
      </Link>

      {/* Header Summary Card */}
      <div className="glass-panel rounded-2xl p-6 lg:p-8 border border-[#1f1f1f] mb-8 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-[#00f0ff]/10 border border-[#00f0ff]/30 flex items-center justify-center text-[#00f0ff]">
              <Terminal className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs text-[#00f0ff] uppercase tracking-wider">{job.module}</span>
                <span className="text-neutral-500">•</span>
                <span className="font-mono text-xs text-neutral-400">{job.job_id}</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white capitalize">
                {job.module.replace(/_/g, ' ')} Execution Detail
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <StatusBadge status={job.status} size="lg" />
            {isRunningOrQueued && (
              <span className="font-mono text-xs text-blue-400 flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-950/40 border border-blue-500/30 animate-pulse">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Polling GET /jobs/{job.job_id}
              </span>
            )}
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6 border-t border-[#1f1f1f] font-mono text-xs">
          <div>
            <span className="text-neutral-500 block mb-1">Tenant Scope:</span>
            <span className="text-white font-semibold">{job.tenant_id}</span>
          </div>
          <div>
            <span className="text-neutral-500 block mb-1">Created At:</span>
            <span className="text-neutral-300">{new Date(job.created_at).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-neutral-500 block mb-1">Celery Queue:</span>
            <span className="text-neutral-300">redis://default:6379/0</span>
          </div>
          <div>
            <span className="text-neutral-500 block mb-1">Artifacts Count:</span>
            <span className="text-[#00f0ff] font-semibold">{job.result?.artifacts?.length ?? 0} files</span>
          </div>
        </div>
      </div>

      {/* Input Payload Card */}
      <div className="glass-panel rounded-2xl p-6 border border-[#1f1f1f] mb-8">
        <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-400 font-mono mb-3 flex items-center gap-2">
          <Code2 className="w-4 h-4 text-[#00f0ff]" /> Input Payload (`run()` parameters)
        </h3>
        <pre className="bg-[#0a0a0a] rounded-xl p-4 border border-[#1a1a1a] font-mono text-xs text-neutral-300 overflow-x-auto">
          {JSON.stringify(job.payload, null, 2)}
        </pre>
      </div>

      {/* Human-in-the-Loop Gate for Notebook to Blog */}
      {job.module === 'notebook_to_blog' && job.result && (
        <ApproveRejectPanel
          jobId={job.job_id}
          isApproved={job.approved}
          isRejected={job.rejected}
          initialFeedback={job.rejection_feedback}
          onActionCompleted={refetch}
        />
      )}

      {/* Module Output Rendering Section */}
      {job.result ? (
        <div className="glass-panel rounded-2xl p-6 lg:p-8 border border-[#1f1f1f] mb-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-[#00f0ff]" />
              Generated Output Content
            </h3>

            {/* Quick action buttons */}
            <div className="flex items-center gap-2">
              {job.result.output?.test_code && (
                <button
                  onClick={() => handleCopyCode(job.result!.output.test_code)}
                  className="px-3 py-1.5 rounded-xl bg-[#141414] hover:bg-[#1f1f1f] border border-[#242424] text-xs font-mono text-neutral-300 flex items-center gap-1.5 transition-all"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied Code' : 'Copy Test Code'}
                </button>
              )}
            </div>
          </div>

          {/* Test Generator Output with Prism Syntax Highlighting */}
          {job.module === 'test_generator' && job.result.output?.test_code ? (
            <div className="rounded-xl overflow-hidden border border-[#242424] bg-[#0d0d0d]">
              <div className="bg-[#141414] px-4 py-2.5 border-b border-[#242424] flex items-center justify-between text-xs font-mono text-neutral-400">
                <span>{job.payload.target_file ? `test_${job.payload.target_file.split('/').pop()}` : 'test_suite.py'}</span>
                <span className="text-emerald-400">{job.result.output.coverage_estimate || '90%+'} Coverage Estimate</span>
              </div>
              <Highlight theme={themes.vsDark} code={job.result.output.test_code} language="python">
                {({ className, style, tokens, getLineProps, getTokenProps }) => (
                  <pre className={`${className} p-5 overflow-x-auto text-xs font-mono leading-relaxed`} style={{ ...style, background: 'transparent' }}>
                    {tokens.map((line, i) => (
                      <div key={i} {...getLineProps({ line })}>
                        <span className="inline-block w-8 text-neutral-600 select-none text-right mr-4">{i + 1}</span>
                        {line.map((token, key) => (
                          <span key={key} {...getTokenProps({ token })} />
                        ))}
                      </div>
                    ))}
                  </pre>
                )}
              </Highlight>
            </div>
          ) : job.module === 'docs_generator' || job.module === 'changelog_generator' ? (
            /* Markdown docs/changelog output rendered cleanly */
            <div className="bg-[#0a0a0a] rounded-xl p-6 border border-[#1f1f1f] prose prose-invert max-w-none text-sm font-sans leading-relaxed">
              <ReactMarkdown>
                {job.result.output?.markdown_docs || job.result.output?.release_notes_md || JSON.stringify(job.result.output, null, 2)}
              </ReactMarkdown>
            </div>
          ) : job.module === 'notebook_to_blog' && job.result.output?.blog_draft_md ? (
            /* Notebook to blog draft rendering */
            <div className="space-y-6">
              <div className="bg-[#0a0a0a] rounded-xl p-6 border border-[#1f1f1f] prose prose-invert max-w-none text-sm font-sans leading-relaxed">
                <ReactMarkdown>{job.result.output.blog_draft_md}</ReactMarkdown>
              </div>

              {job.result.output.images && job.result.output.images.length > 0 && (
                <div className="pt-4 border-t border-[#1f1f1f]">
                  <h4 className="font-mono text-xs text-neutral-400 uppercase tracking-wider mb-3">Extracted S3 Output Images</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {job.result.output.images.map((img: string, idx: number) => (
                      <div key={idx} className="rounded-xl overflow-hidden border border-[#242424] bg-[#0a0a0a]">
                        <img src={img} alt={`Cell output ${idx + 1}`} className="w-full h-auto object-cover max-h-64" />
                        <div className="p-2.5 text-[11px] font-mono text-neutral-400 bg-[#141414]">s3://shipfaster-artifacts/image_{idx + 1}.png</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Scaffolder or generic output */
            <pre className="bg-[#0a0a0a] rounded-xl p-5 border border-[#1a1a1a] font-mono text-xs text-neutral-300 overflow-x-auto">
              {JSON.stringify(job.result.output, null, 2)}
            </pre>
          )}

          {/* Artifacts Download Section */}
          {job.result.artifacts && job.result.artifacts.length > 0 && (
            <div className="mt-8 pt-6 border-t border-[#1f1f1f]">
              <h4 className="text-xs font-mono uppercase tracking-wider text-neutral-400 mb-3">
                S3 Artifact Storage References
              </h4>
              <div className="space-y-2 font-mono text-xs">
                {job.result.artifacts.map((art, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-xl bg-[#0a0a0a] border border-[#1a1a1a] hover:border-[#00f0ff]/30 transition-colors"
                  >
                    <span className="text-neutral-300 truncate">{art}</span>
                    <button
                      onClick={() => window.open(`http://localhost:8000/api/v1/artifacts/download-file?key=${encodeURIComponent(`${job.tenant_id}/${job.job_id}/${art}`)}`, '_blank')}
                      className="px-3 py-1 rounded-lg bg-[#141414] hover:bg-[#00f0ff] hover:text-[#0a0a0a] text-neutral-300 font-semibold transition-all flex items-center gap-1.5 shrink-0"
                    >
                      <Download className="w-3.5 h-3.5" /> Download
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-10 text-center border border-[#1f1f1f]">
          <Loader2 className="w-8 h-8 animate-spin text-[#00f0ff] mx-auto mb-3" />
          <h3 className="text-base font-bold text-white mb-1">Waiting on Celery Worker Execution</h3>
          <p className="text-xs text-neutral-400 font-mono max-w-md mx-auto">
            The job is currently <span className="text-[#00f0ff]">{job.status}</span>. Dev 1's LLM module is processing inputs and generating output artifacts.
          </p>
        </div>
      )}
    </div>
  );
};
