import clsx from 'clsx';

const styles: Record<string, string> = {
  created: 'border-slate-400 text-slate-700',
  documents_uploaded: 'border-blue-400 text-blue-700',
  extracted: 'border-indigo-400 text-indigo-700',
  analyzed: 'border-purple-400 text-purple-700',
  pending_review: 'border-amber-400 text-amber-700',
  approved: 'bg-emerald-600 border-emerald-600 text-white',
  closed: 'bg-slate-600 border-slate-600 text-white',
  cancelled: 'bg-red-600 border-red-600 text-white'
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx('inline-flex items-center rounded border px-2 py-1 text-xs font-medium', styles[status] ?? styles.created)}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}
