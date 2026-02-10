import { useState } from 'react';

import { PageHeader } from '../components/shared/PageHeader';
import { useApplications, useCreateApplication } from '../hooks/useApplications';
import { formatDate } from '../lib/utils';

export function ApplicationsPage() {
  const { data: applications = [], isLoading } = useApplications();
  const createApplication = useCreateApplication();

  const [name, setName] = useState('');
  const [reviewType, setReviewType] = useState('user_access');
  const [owner, setOwner] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [criticality, setCriticality] = useState('high');
  const [classification, setClassification] = useState('confidential');

  async function onCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createApplication.mutateAsync({
      name,
      review_type: reviewType,
      owner,
      owner_email: ownerEmail,
      criticality,
      data_classification: classification,
      review_frequency: 'quarterly'
    });

    setName('');
    setOwner('');
    setOwnerEmail('');
  }

  return (
    <div>
      <PageHeader title="Applications" subtitle="Application registry and review schedule controls" />

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <section className="rounded border border-slate-200 bg-white">
          <header className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-800">Configured Applications</h2>
          </header>

          {isLoading ? (
            <p className="p-4 text-sm text-slate-600">Loading applications...</p>
          ) : applications.length === 0 ? (
            <p className="p-4 text-sm text-slate-600">No applications configured.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Criticality</th>
                    <th className="px-4 py-3">Classification</th>
                    <th className="px-4 py-3">Next Review</th>
                  </tr>
                </thead>
                <tbody>
                  {applications.map((app) => (
                    <tr key={app.id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-slate-800">{app.name}</td>
                      <td className="px-4 py-3 text-slate-700">{app.review_type}</td>
                      <td className="px-4 py-3 text-slate-700">{app.criticality}</td>
                      <td className="px-4 py-3 text-slate-700">{app.data_classification}</td>
                      <td className="px-4 py-3 text-slate-700">{formatDate(app.next_review_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-800">Add Application</h2>

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
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Owner</label>
              <input
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Owner Email</label>
              <input
                type="email"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Criticality</label>
                <select
                  value={criticality}
                  onChange={(e) => setCriticality(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Classification</label>
                <select
                  value={classification}
                  onChange={(e) => setClassification(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="restricted">Restricted</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={createApplication.isPending}
              className="w-full rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {createApplication.isPending ? 'Saving...' : 'Add Application'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
