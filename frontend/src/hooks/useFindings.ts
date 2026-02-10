import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { Finding } from '../types';

export function useFindings(reviewId: string | null) {
  return useQuery({
    queryKey: ['findings', reviewId],
    queryFn: async () => {
      if (!reviewId) return [];
      const resp = await api.get<Finding[]>(`/reviews/${reviewId}/findings`);
      return resp.data;
    },
    enabled: Boolean(reviewId)
  });
}

export function useUpdateFinding(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      findingId: string;
      disposition?: string;
      disposition_note?: string;
      status?: string;
      notes?: string;
    }) => {
      const { findingId, ...updatePayload } = payload;
      const resp = await api.put<Finding>(`/reviews/${reviewId}/findings/${findingId}`, updatePayload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['findings', reviewId] });
    }
  });
}

export function useBulkDisposition(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { finding_ids: string[]; disposition: string; justification: string }) => {
      const resp = await api.post(`/reviews/${reviewId}/findings/bulk-disposition`, payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['findings', reviewId] });
    }
  });
}
