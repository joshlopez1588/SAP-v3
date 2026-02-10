import { useState } from 'react';

import { PageHeader } from '../components/shared/PageHeader';
import { useAuditEntries, useVerifyAuditChain } from '../hooks/useAudit';
import { formatDateTime } from '../lib/utils';

export function AuditLogPage() {
  const { data: entries = [], isLoading } = useAuditEntries();
  const verify = useVerifyAuditChain();
  const [verificationMessage, setVerificationMessage] = useState<string>('');

  async function onVerify() {
    const result = await verify.mutateAsync();
    setVerificationMessage(`${result.message} (${result.checked_entries} entries)`);
  }

  return (
    <div>
      <PageHeader
        title="Audit Log"
        subtitle="Immutable hash-chained event history"
        actions={
          <button
            onClick={onVerify}
            className="rounded border border-brand-400 px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50"
          >
            Verify Hash Chain
          </button>
        }
      />

      {verificationMessage ? (
        <p className="mb-4 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{verificationMessage}</p>
      ) : null}

      <section className="rounded border border-slate-200 bg-white">
        <header className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Audit Entries</h2>
        </header>

        {isLoading ? (
          <p className="p-4 text-sm text-slate-600">Loading audit data...</p>
        ) : entries.length === 0 ? (
          <p className="p-4 text-sm text-slate-600">No audit entries.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Actor</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Entity</th>
                  <th className="px-4 py-3">Hash</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 text-slate-700">{formatDateTime(entry.timestamp)}</td>
                    <td className="px-4 py-3 text-slate-700">{entry.actor_id || 'system'}</td>
                    <td className="px-4 py-3 text-slate-700">{entry.action}</td>
                    <td className="px-4 py-3 text-slate-700">{entry.entity_type}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{entry.content_hash.slice(0, 18)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
