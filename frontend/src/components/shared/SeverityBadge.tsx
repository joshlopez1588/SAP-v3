import clsx from 'clsx';

const styles: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  medium: 'bg-amber-100 text-amber-800 border-amber-300',
  low: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  info: 'bg-blue-100 text-blue-800 border-blue-300'
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      aria-label={`${severity} severity`}
      className={clsx(
        'inline-flex items-center rounded border px-2 py-1 text-xs font-semibold uppercase tracking-wide',
        styles[severity] ?? styles.info
      )}
    >
      {severity}
    </span>
  );
}
