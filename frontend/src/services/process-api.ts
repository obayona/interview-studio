import { apiClient } from './api-client';
import type {
  InterviewProcess,
  ProcessDraft,
  ProcessSummary,
} from '../types/process';

export const processApi = {
  list: () => apiClient.request<ProcessSummary[]>('/api/v1/processes'),
  get: (id: string) =>
    apiClient.request<InterviewProcess>(
      `/api/v1/processes/${encodeURIComponent(id)}`,
    ),
  create: (draft: ProcessDraft) =>
    apiClient.request<InterviewProcess>('/api/v1/processes', {
      method: 'POST',
      body: JSON.stringify(draft),
    }),
  update: (id: string, draft: ProcessDraft) =>
    apiClient.request<InterviewProcess>(
      `/api/v1/processes/${encodeURIComponent(id)}`,
      { method: 'PATCH', body: JSON.stringify(draft) },
    ),
  remove: (id: string) =>
    apiClient.request<void>(`/api/v1/processes/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
  preview: (url: string) =>
    apiClient.request<{ url: string; content: string }>(
      '/api/v1/processes/import-preview',
      { method: 'POST', body: JSON.stringify({ url }) },
    ),
  startAttempt: (processId: string, stageId: string) =>
    apiClient.request<{ id: string; attempt_number: number; status: string }>(
      `/api/v1/processes/${encodeURIComponent(processId)}/stages/${encodeURIComponent(stageId)}/attempts`,
      { method: 'POST' },
    ),
  deleteAttempt: (attemptId: string) =>
    apiClient.request<void>(
      `/api/v1/attempts/${encodeURIComponent(attemptId)}`,
      { method: 'DELETE' },
    ),
};
