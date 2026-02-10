import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import { PageHeader } from '../components/shared/PageHeader';
import { SeverityBadge } from '../components/shared/SeverityBadge';
import { StatusBadge } from '../components/shared/StatusBadge';
import { useFindings, useUpdateFinding } from '../hooks/useFindings';
import {
  useAnalyzeReview,
  useApproveReview,
  useConfirmExtraction,
  useExtractDocument,
  useReview,
  useReviewDocuments,
  useUploadDocument
} from '../hooks/useReviews';
import { fileSize, formatDate, formatDateTime } from '../lib/utils';
import type { Finding } from '../types';

function dispositionProgress(findings: Finding[]): string {
  const completed = findings.filter((item) => Boolean(item.disposition)).length;
  return `${completed}/${findings.length}`;
}

export function ReviewWorkspacePage() {
  const params = useParams<{ reviewId: string }>();
  const reviewId = params.reviewId as string;

  const { data: review } = useReview(reviewId);
  const { data: documents = [] } = useReviewDocuments(reviewId);
  const { data: findings = [] } = useFindings(reviewId);

  const uploadDocument = useUploadDocument(reviewId);
  const extractDocument = useExtractDocument(reviewId);
  const confirmExtraction = useConfirmExtraction(reviewId);
  const analyzeReview = useAnalyzeReview(reviewId);
  const updateFinding = useUpdateFinding(reviewId);
  const approveReview = useApproveReview(reviewId);

  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [dispositionNote, setDispositionNote] = useState('');
  const [attestation, setAttestation] = useState('I attest this review is complete.');

  const selectedFinding = useMemo(
    () => findings.find((item) => item.id === selectedFindingId) ?? findings[0],
    [findings, selectedFindingId]
  );

  async function onUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    await uploadDocument.mutateAsync({ file, documentRole: 'primary' });
    event.target.value = '';
  }

  async function onDisposition(disposition: string) {
    if (!selectedFinding) return;
    await updateFinding.mutateAsync({
      findingId: selectedFinding.id,
      disposition,
      disposition_note: dispositionNote || `${disposition} by reviewer`
    });
    setDispositionNote('');
  }

  if (!review) {
    return <div className="text-sm text-slate-600">Loading review...</div>;
  }

  return (
    <div>
      <PageHeader
        title={review.name}
        subtitle={`Period: ${formatDate(review.period_start)} - ${formatDate(review.period_end)} | Framework ${review.framework_version_label}`}
        actions={<StatusBadge status={review.status} />}
      />

      <section className="grid gap-4 md:grid-cols-4">
        <article className="rounded border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Documents</p>
          <p className="mt-2 text-xl font-bold text-slate-900">{documents.length}</p>
        </article>
        <article className="rounded border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Findings</p>
          <p className="mt-2 text-xl font-bold text-slate-900">{findings.length}</p>
        </article>
        <article className="rounded border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Disposition Progress</p>
          <p className="mt-2 text-xl font-bold text-slate-900">{dispositionProgress(findings)}</p>
        </article>
        <article className="rounded border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Checksum</p>
          <p className="mt-2 truncate text-xs font-semibold text-slate-700">{review.analysis_checksum || '--'}</p>
        </article>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[420px_1fr]">
        <div className="space-y-6">
          <article className="rounded border border-slate-200 bg-white">
            <header className="border-b border-slate-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-800">Documents</h2>
            </header>
            <div className="space-y-3 p-4">
              <label className="inline-flex cursor-pointer items-center justify-center rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700">
                Upload Document
                <input type="file" className="hidden" onChange={onUpload} />
              </label>
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div key={doc.id} className="rounded border border-slate-200 p-3 text-sm">
                    <p className="font-medium text-slate-800">{doc.filename}</p>
                    <p className="mt-1 text-xs text-slate-600">
                      {fileSize(doc.file_size)} | Match {(doc.template_match_confidence ?? 0).toFixed(2)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Uploaded {formatDateTime(doc.uploaded_at)}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        onClick={() => extractDocument.mutate(doc.id)}
                        className="rounded border border-brand-300 px-2 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-50"
                      >
                        Extract
                      </button>
                      <button
                        onClick={() => confirmExtraction.mutate(doc.id)}
                        className="rounded border border-emerald-300 px-2 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-50"
                      >
                        Confirm
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => analyzeReview.mutate()}
                className="w-full rounded bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Run Deterministic Analysis
              </button>
            </div>
          </article>

          <article className="rounded border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-800">Final Approval</h2>
            <textarea
              value={attestation}
              onChange={(e) => setAttestation(e.target.value)}
              rows={3}
              className="mt-3 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              onClick={() => approveReview.mutate(attestation)}
              className="mt-3 w-full rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              Sign Off and Approve
            </button>
          </article>
        </div>

        <article className="rounded border border-slate-200 bg-white">
          <header className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-800">Findings Workspace</h2>
          </header>
          <div className="grid min-h-[560px] grid-cols-1 xl:grid-cols-[360px_1fr]">
            <aside className="border-r border-slate-200 p-3">
              <ul className="space-y-2" role="listbox" aria-label="Findings list">
                {findings.map((finding) => (
                  <li key={finding.id}>
                    <button
                      className={`w-full rounded border p-3 text-left ${
                        selectedFinding?.id === finding.id ? 'border-brand-400 bg-brand-50' : 'border-slate-200 bg-white'
                      }`}
                      onClick={() => setSelectedFindingId(finding.id)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <SeverityBadge severity={finding.severity} />
                        <span className="text-xs text-slate-500">{finding.record_count} recs</span>
                      </div>
                      <p className="mt-2 text-sm font-semibold text-slate-800">{finding.check_name}</p>
                      <p className="mt-1 text-xs text-slate-600">Disposition: {finding.disposition || 'Pending'}</p>
                    </button>
                  </li>
                ))}
              </ul>
            </aside>

            <div className="p-4">
              {selectedFinding ? (
                <div>
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={selectedFinding.severity} />
                    <h3 className="text-lg font-semibold text-slate-900">{selectedFinding.check_name}</h3>
                  </div>

                  <p className="mt-4 rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    {selectedFinding.explainability}
                  </p>

                  <div className="mt-4 rounded border border-violet-200 bg-violet-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">AI-Generated Description</p>
                    <p className="mt-2 text-sm text-slate-700">{selectedFinding.ai_description || 'No enrichment yet.'}</p>
                  </div>

                  <div className="mt-4">
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Disposition Justification
                    </label>
                    <textarea
                      value={dispositionNote}
                      onChange={(e) => setDispositionNote(e.target.value)}
                      rows={3}
                      className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                    />
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        onClick={() => onDisposition('approved')}
                        className="rounded border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => onDisposition('revoke')}
                        className="rounded border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700"
                      >
                        Revoke
                      </button>
                      <button
                        onClick={() => onDisposition('abstain')}
                        className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700"
                      >
                        Abstain
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-600">No findings available.</p>
              )}
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
