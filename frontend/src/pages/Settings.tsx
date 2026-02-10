import { useQuery } from '@tanstack/react-query';

import { PageHeader } from '../components/shared/PageHeader';
import { api } from '../lib/api';

function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const resp = await api.get<Record<string, unknown>>('/settings');
      return resp.data;
    }
  });
}

export function SettingsPage() {
  const { data: settings, isLoading } = useSettings();

  return (
    <div>
      <PageHeader title="Settings" subtitle="System-level security and operational defaults" />
      <section className="rounded border border-slate-200 bg-white p-4">
        {isLoading ? (
          <p className="text-sm text-slate-600">Loading settings...</p>
        ) : (
          <pre className="overflow-x-auto rounded bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(settings, null, 2)}
          </pre>
        )}
      </section>
    </div>
  );
}
