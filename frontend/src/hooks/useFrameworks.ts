import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { Framework } from '../types';

export function useFrameworks() {
  return useQuery({
    queryKey: ['frameworks'],
    queryFn: async () => {
      const resp = await api.get<Framework[]>('/frameworks');
      return resp.data;
    }
  });
}

export function useCreateFramework() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      description?: string;
      review_type: string;
      settings: Record<string, unknown>;
      checks: Array<Record<string, unknown>>;
      regulatory_mappings: Array<Record<string, unknown>>;
    }) => {
      const resp = await api.post<Framework>('/frameworks', payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['frameworks'] });
    }
  });
}
