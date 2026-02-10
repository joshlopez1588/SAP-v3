import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { Application } from '../types';

export function useApplications() {
  return useQuery({
    queryKey: ['applications'],
    queryFn: async () => {
      const resp = await api.get<Application[]>('/applications');
      return resp.data;
    }
  });
}

export function useCreateApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      description?: string;
      review_type: string;
      owner?: string;
      owner_email?: string;
      criticality: string;
      data_classification: string;
      review_frequency: string;
    }) => {
      const resp = await api.post<Application>('/applications', payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
    }
  });
}
