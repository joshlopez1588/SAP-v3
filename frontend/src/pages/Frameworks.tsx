import { useMemo, useState } from 'react';

import { PageHeader } from '../components/shared/PageHeader';
import { useCreateFramework, useFrameworks } from '../hooks/useFrameworks';

const STARTER_CHECKS = [
  {
    id: 'inactive_accounts',
    name: 'Inactive Accounts',
    default_severity: 'medium',
    enabled: true,
    condition: {
      type: 'compound',
      operator: 'AND',
      conditions: [
        { field: 'status', operator: 'equals', value: 'active' },
        { field: 'last_activity', operator: 'older_than_days', value: '${settings.inactive_threshold_days}' }
      ]
    },
    output_fields: ['identifier', 'display_name', 'email', 'status', 'last_activity']
  }
];

export function FrameworksPage() {
  const { data: frameworks = [], isLoading } = useFrameworks();
  const createFramework = useCreateFramework();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [reviewType, setReviewType] = useState('user_access');

  const publishedCount = useMemo(() => frameworks.filter((f) => f.status === 'published').length, [frameworks]);

  async function onCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createFramework.mutateAsync({
      name,
      description,
      review_type: reviewType,
      settings: { inactive_threshold_days: 90, high_limit_threshold: 1000000 },
      checks: STARTER_CHECKS,
      regulatory_mappings: [{ framework: 'FFIEC', category: 'Access Management' }]
    });
    setName('');
    setDescription('');
  }

  return (
    <div>
      <PageHeader title="Frameworks" subtitle={`Published: ${publishedCount} | Total: ${frameworks.length}`} />

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <section className="rounded border border-slate-200 bg-white">
          <header className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-800">Framework Library</h2>
          </header>
          {isLoading ? (
            <p className="p-4 text-sm text-slate-600">Loading frameworks...</p>
          ) : frameworks.length === 0 ? (
            <p className="p-4 text-sm text-slate-600">No frameworks yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Checks</th>
                  </tr>
                </thead>
                <tbody>
                  {frameworks.map((framework) => (
                    <tr key={framework.id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-slate-800">{framework.name}</td>
                      <td className="px-4 py-3 text-slate-700">{framework.review_type}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {framework.version_major}.{framework.version_minor}.{framework.version_patch}
                      </td>
                      <td className="px-4 py-3 text-slate-700">{framework.status}</td>
                      <td className="px-4 py-3 text-slate-700">{framework.checks.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-800">Create Framework</h2>
          <form className="mt-4 space-y-3" onSubmit={onCreate}>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Review Type</label>
              <select
                value={reviewType}
                onChange={(e) => setReviewType(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="user_access">User Access</option>
                <option value="firewall_rule">Firewall Rule</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={createFramework.isPending}
              className="w-full rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {createFramework.isPending ? 'Creating...' : 'Create Draft'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
