import { apiClient } from './api-client';
import type { SettingsResponse, SettingsUpdate } from '../types/api';

export const settingsApi = {
  get: () => apiClient.request<SettingsResponse>('/api/v1/settings'),
  update: (values: SettingsUpdate) =>
    apiClient.request<SettingsResponse>('/api/v1/settings', {
      method: 'PATCH',
      body: JSON.stringify(values),
    }),
  remove: (key: string) =>
    apiClient.request<SettingsResponse>(
      `/api/v1/settings/${encodeURIComponent(key)}`,
      {
        method: 'DELETE',
      },
    ),
  testProvider: () =>
    apiClient.request<{ ok: boolean; message: string }>(
      '/api/v1/settings/test-provider',
      {
        method: 'POST',
        body: JSON.stringify({ provider: 'openai' }),
      },
    ),
};
