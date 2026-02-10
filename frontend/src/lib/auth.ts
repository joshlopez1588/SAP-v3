import { api } from './api';
import { useAuthStore } from '../stores/authStore';
import type { User } from '../types';

interface LoginPayload {
  email: string;
  password: string;
}

interface RegisterPayload extends LoginPayload {
  name: string;
  invite_code: string;
}

interface TokenResponse {
  access_token: string;
  access_token_expires_at: string;
}

export async function login(payload: LoginPayload): Promise<User> {
  const tokenResp = await api.post<TokenResponse>('/auth/login', payload);
  useAuthStore.getState().setAccessToken(tokenResp.data.access_token);

  const meResp = await api.get<User>('/auth/me');
  useAuthStore.getState().setUser(meResp.data);
  return meResp.data;
}

export async function register(payload: RegisterPayload): Promise<User> {
  const response = await api.post<User>('/auth/register', payload);
  return response.data;
}

export async function refreshSession(): Promise<User | null> {
  try {
    const tokenResp = await api.post<TokenResponse>('/auth/refresh');
    useAuthStore.getState().setAccessToken(tokenResp.data.access_token);

    const meResp = await api.get<User>('/auth/me');
    useAuthStore.getState().setUser(meResp.data);
    return meResp.data;
  } catch {
    useAuthStore.getState().clear();
    return null;
  }
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout');
  } finally {
    useAuthStore.getState().clear();
  }
}
