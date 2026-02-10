import { useState } from 'react';

import { PageHeader } from '../components/shared/PageHeader';
import { useReferenceDatasets, useUploadReferenceDataset } from '../hooks/useReferenceData';
import { formatDate } from '../lib/utils';

export function ReferenceDataPage() {
  const { data: datasets = [], isLoading } = useReferenceDatasets();
  const uploadDataset = useUploadReferenceDataset();

  const [name, setName] = useState('HR Active Employees');
  const [dataType, setDataType] = useState('hr_employees');
  const [sourceSystem, setSourceSystem] = useState('workday');
  const [freshnessDays, setFreshnessDays] = useState(30);
  const [file, setFile] = useState<File | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;

    await uploadDataset.mutateAsync({
      name,
      dataType,
      sourceSystem,
      freshnessThresholdDays: freshnessDays,
      file
    });
    setFile(null);
  }

  return (
    <div>
      <PageHeader title="Reference Data" subtitle="Upload HR and supporting datasets for cross-document correlation" />

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <section className="rounded border border-slate-200 bg-white">
          <header className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-800">Dataset Library</h2>
          </header>

          {isLoading ? (
            <p className="p-4 text-sm text-slate-600">Loading datasets...</p>
          ) : datasets.length === 0 ? (
            <p className="p-4 text-sm text-slate-600">No datasets uploaded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Records</th>
                    <th className="px-4 py-3">Freshness</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((dataset) => (
                    <tr key={dataset.id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-slate-800">{dataset.name}</td>
                      <td className="px-4 py-3 text-slate-700">{dataset.data_type}</td>
                      <td className="px-4 py-3 text-slate-700">{dataset.source_system}</td>
                      <td className="px-4 py-3 text-slate-700">{dataset.record_count}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded px-2 py-1 text-xs font-semibold uppercase tracking-wide ${
                            dataset.freshness_status === 'green'
                              ? 'bg-emerald-100 text-emerald-700'
                              : dataset.freshness_status === 'amber'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {dataset.freshness_status}
                        </span>
                        <p className="mt-1 text-xs text-slate-500">Uploaded {formatDate(dataset.uploaded_at)}</p>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-800">Upload Dataset</h2>
          <form className="mt-4 space-y-3" onSubmit={onSubmit}>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Data Type</label>
              <input
                value={dataType}
                onChange={(e) => setDataType(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Source System</label>
              <input
                value={sourceSystem}
                onChange={(e) => setSourceSystem(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Freshness Threshold (Days)</label>
              <input
                type="number"
                value={freshnessDays}
                onChange={(e) => setFreshnessDays(Number(e.target.value))}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">File</label>
              <input
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                required
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={uploadDataset.isPending || !file}
              className="w-full rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {uploadDataset.isPending ? 'Uploading...' : 'Upload'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
