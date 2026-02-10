import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { DocumentItem, Review } from '../types';

export function useReviews() {
  return useQuery({
    queryKey: ['reviews'],
    queryFn: async () => {
      const resp = await api.get<Review[]>('/reviews');
      return resp.data;
    }
  });
}

export function useReview(reviewId: string | null) {
  return useQuery({
    queryKey: ['review', reviewId],
    queryFn: async () => {
      if (!reviewId) return null;
      const resp = await api.get<Review>(`/reviews/${reviewId}`);
      return resp.data;
    },
    enabled: Boolean(reviewId)
  });
}

export function useCreateReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      application_id: string;
      framework_id: string;
      period_start?: string;
      period_end?: string;
      due_date?: string;
      assigned_to?: string;
    }) => {
      const resp = await api.post<Review>('/reviews', payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    }
  });
}

export function useReviewDocuments(reviewId: string | null) {
  return useQuery({
    queryKey: ['review-documents', reviewId],
    queryFn: async () => {
      if (!reviewId) return [];
      const resp = await api.get<DocumentItem[]>(`/reviews/${reviewId}/documents`);
      return resp.data;
    },
    enabled: Boolean(reviewId)
  });
}

export function useUploadDocument(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { file: File; documentRole: string }) => {
      const formData = new FormData();
      formData.append('file', payload.file);
      formData.append('document_role', payload.documentRole);
      const resp = await api.post(`/reviews/${reviewId}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-documents', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    }
  });
}

export function useExtractDocument(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string) => {
      const resp = await api.post(`/reviews/${reviewId}/documents/${documentId}/extract`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    }
  });
}

export function useConfirmExtraction(reviewId: string) {
  return useMutation({
    mutationFn: async (documentId: string) => {
      const resp = await api.post(`/reviews/${reviewId}/documents/${documentId}/confirm`);
      return resp.data;
    }
  });
}

export function useAnalyzeReview(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const resp = await api.post(`/reviews/${reviewId}/analyze`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['findings', reviewId] });
    }
  });
}

export function useApproveReview(reviewId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (attestation: string) => {
      const formData = new FormData();
      formData.append('attestation', attestation);
      const resp = await api.post(`/reviews/${reviewId}/approve`, formData);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    }
  });
}
