import { useMemo } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '../components/shared/PageHeader';
import { StatusBadge } from '../components/shared/StatusBadge';
import { useReviews } from '../hooks/useReviews';
import { formatDate } from '../lib/utils';

export function DashboardPage() {
  const { data: reviews = [], isLoading } = useReviews();

  const openCount = useMemo(() => reviews.filter((r) => !['closed', 'cancelled'].includes(r.status)).length, [reviews]);
  const approvedCount = useMemo(() => reviews.filter((r) => r.status === 'approved').length, [reviews]);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Operational view of review workflow and compliance readiness"
        actions={
          <Link to="/reviews" className="rounded bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            Open Reviews
          </Link>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-700">Total Reviews</h2>
          <p className="mt-2 text-3xl font-bold text-slate-900">{reviews.length}</p>
        </article>
        <article className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-700">Open Reviews</h2>
          <p className="mt-2 text-3xl font-bold text-brand-700">{openCount}</p>
        </article>
        <article className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-700">Approved Reviews</h2>
          <p className="mt-2 text-3xl font-bold text-emerald-700">{approvedCount}</p>
        </article>
      </section>

      <section className="mt-6 rounded border border-slate-200 bg-white">
        <header className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Active Reviews</h2>
        </header>
        {isLoading ? (
          <p className="p-4 text-sm text-slate-600">Loading reviews...</p>
        ) : reviews.length === 0 ? (
          <div className="p-6 text-sm text-slate-600">
            No reviews yet. <Link to="/reviews" className="font-semibold text-brand-700">Create your first review</Link>.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-3">Review</th>
                  <th className="px-4 py-3">Framework Version</th>
                  <th className="px-4 py-3">Due Date</th>
                  <th className="px-4 py-3">Status</th>
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
                    <td className="px-4 py-3 text-slate-700">{review.framework_version_label}</td>
                    <td className="px-4 py-3 text-slate-700">{formatDate(review.due_date)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={review.status} />
                    </td>
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
