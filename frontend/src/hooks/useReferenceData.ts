import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { ReferenceDataset } from '../types';

export function useReferenceDatasets() {
  return useQuery({
    queryKey: ['reference-datasets'],
    queryFn: async () => {
      const resp = await api.get<ReferenceDataset[]>('/reference-datasets');
      return resp.data;
    }
  });
}

export function useUploadReferenceDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      dataType: string;
      sourceSystem: string;
      freshnessThresholdDays: number;
      file: File;
    }) => {
      const formData = new FormData();
      formData.append('name', payload.name);
      formData.append('data_type', payload.dataType);
      formData.append('source_system', payload.sourceSystem);
      formData.append('freshness_threshold_days', String(payload.freshnessThresholdDays));
      formData.append('file', payload.file);

      const resp = await api.post('/reference-datasets', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reference-datasets'] });
    }
  });
}
