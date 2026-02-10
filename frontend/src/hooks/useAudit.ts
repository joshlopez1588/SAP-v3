import { useMutation, useQuery } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { AuditEntry } from '../types';

export function useAuditEntries() {
  return useQuery({
    queryKey: ['audit'],
    queryFn: async () => {
      const resp = await api.get<AuditEntry[]>('/audit');
      return resp.data;
    }
  });
}

export function useVerifyAuditChain() {
  return useMutation({
    mutationFn: async () => {
      const resp = await api.post('/audit/verify');
      return resp.data as { valid: boolean; checked_entries: number; message: string };
    }
  });
}
