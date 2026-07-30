import { apiClient } from './api-client';
import type { EvaluationReport, ProcessReport } from '../types/report';

export const reportApi = {
  getAttempt: (attemptId: string) =>
    apiClient.request<EvaluationReport>(
      `/api/v1/attempts/${encodeURIComponent(attemptId)}/report`,
    ),
  evaluate: (attemptId: string) =>
    apiClient.request<EvaluationReport>(
      `/api/v1/attempts/${encodeURIComponent(attemptId)}/report`,
      { method: 'POST' },
    ),
  getProcess: (processId: string) =>
    apiClient.request<ProcessReport>(
      `/api/v1/processes/${encodeURIComponent(processId)}/report`,
    ),
};
