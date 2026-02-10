import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/shared/PageHeader';
import { StatusBadge } from '../components/shared/StatusBadge';
import { useApplications } from '../hooks/useApplications';
import { useFrameworks } from '../hooks/useFrameworks';
import { useCreateReview, useReviews } from '../hooks/useReviews';
import { formatDate } from '../lib/utils';

export function ReviewsPage() {
  const { data: reviews = [], isLoading } = useReviews();
  const { data: applications = [] } = useApplications();
  const { data: frameworks = [] } = useFrameworks();
  const createReview = useCreateReview();

  const [name, setName] = useState('');
  const [applicationId, setApplicationId] = useState('');
  const [frameworkId, setFrameworkId] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [dueDate, setDueDate] = useState('');

  const selectedApplication = useMemo(
    () => applications.find((app) => app.id === applicationId),
    [applications, applicationId]
  );

  const compatibleFrameworks = useMemo(
    () => frameworks.filter((framework) => framework.review_type === selectedApplication?.review_type),
    [frameworks, selectedApplication]
  );

  async function onCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createReview.mutateAsync({
      name,
      application_id: applicationId,
      framework_id: frameworkId,
      period_start: periodStart || undefined,
      period_end: periodEnd || undefined,
      due_date: dueDate || undefined
    });

    setName('');
    setPeriodStart('');
    setPeriodEnd('');
    setDueDate('');
  }

  return (
    <div>
      <PageHeader title="Reviews" subtitle="Create and execute periodic security reviews" />

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <section className="rounded border border-slate-200 bg-white">
          <header className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-800">Review Registry</h2>
          </header>

          {isLoading ? (
            <p className="p-4 text-sm text-slate-600">Loading reviews...</p>
          ) : reviews.length === 0 ? (
            <p className="p-4 text-sm text-slate-600">No reviews yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Period</th>
                    <th className="px-4 py-3">Due Date</th>
                  </tr>
                </thead>
                <tbody>
                  {reviews.map((review) => (
                    <tr key={review.id} className="border-t border-slate-100">
                      <td className="px-4 py-3">
                        <Link to={`/reviews/${review.id}`} className="font-medium text-brand-700 hover:text-brand-800">
                          {review.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={review.status} />
                      </td>
                      <td className="px-4 py-3 text-slate-700">
                        {formatDate(review.period_start)} - {formatDate(review.period_end)}
                      </td>
                      <td className="px-4 py-3 text-slate-700">{formatDate(review.due_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-800">Create Review</h2>

          <form className="mt-4 space-y-3" onSubmit={onCreate}>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Review Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Application</label>
              <select
                value={applicationId}
                onChange={(e) => {
                  setApplicationId(e.target.value);
                  setFrameworkId('');
                }}
                required
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select application</option>
                {applications.map((app) => (
                  <option key={app.id} value={app.id}>
                    {app.name} ({app.review_type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Framework</label>
              <select
                value={frameworkId}
                onChange={(e) => setFrameworkId(e.target.value)}
                required
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                disabled={!selectedApplication}
              >
                <option value="">Select framework</option>
                {compatibleFrameworks.map((framework) => (
                  <option key={framework.id} value={framework.id}>
                    {framework.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Period Start</label>
                <input
                  type="date"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Period End</label>
                <input
                  type="date"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Due Date</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={createReview.isPending}
              className="w-full rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {createReview.isPending ? 'Creating...' : 'Create Review'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
