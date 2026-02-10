import { useState } from 'react';

import { PageHeader } from '../components/shared/PageHeader';
import { api } from '../lib/api';

export function ReportsPage() {
  const [status, setStatus] = useState<string>('');

  async function generateTrend() {
    const response = await api.post('/reports/trend', { period: '12_months' });
    setStatus(`Trend report ${response.data.status}`);
  }

  async function generateExceptions() {
    const response = await api.post('/reports/exceptions', { includeClosed: false });
    setStatus(`Exceptions report ${response.data.status}`);
  }

  return (
    <div>
      <PageHeader title="Reports" subtitle="Generate review, compliance, and evidence reports" />
      <section className="rounded border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap gap-3">
          <button onClick={generateTrend} className="rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            Generate Trend Report
          </button>
          <button
            onClick={generateExceptions}
            className="rounded border border-brand-400 px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50"
          >
            Generate Exceptions Report
          </button>
        </div>
        {status ? <p className="mt-4 text-sm text-slate-700">{status}</p> : null}
      </section>
    </div>
  );
}
