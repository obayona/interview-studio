import { apiClient } from './api-client';

export interface TranscriptMessage {
  id: string;
  sequence: number;
  role: 'user' | 'assistant';
  text: string;
  created_at: string;
}

export const interviewApi = {
  history: (attemptId: string) =>
    apiClient.request<{
      attempt_id: string;
      status: string;
      messages: TranscriptMessage[];
    }>(`/api/v1/interviews/${encodeURIComponent(attemptId)}/history`),
};
