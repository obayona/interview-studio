import { apiClient } from './api-client';
import type { DashboardData } from '../types/dashboard';

export const dashboardApi = {
  get: () => apiClient.request<DashboardData>('/api/v1/dashboard'),
};
