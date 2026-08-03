import { apiClient } from './api-client';

export interface AuthSession {
  authenticated: boolean;
  username: string;
  csrf_token: string;
  expires_at: string;
}

export const authApi = {
  login: async (username: string, password: string) => {
    const session = await apiClient.request<AuthSession>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    apiClient.setCsrfToken(session.csrf_token);
    return session;
  },
  session: async () => {
    const session = await apiClient.request<AuthSession>(
      '/api/v1/auth/session',
    );
    apiClient.setCsrfToken(session.csrf_token);
    return session;
  },
  logout: async () => {
    await apiClient.request<void>('/api/v1/auth/logout', { method: 'POST' });
    apiClient.setCsrfToken('');
  },
};
