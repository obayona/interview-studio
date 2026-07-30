import { apiClient } from './api-client';
import type {
  DeveloperProfile,
  ProfileDraft,
  ProfileSuggestions,
} from '../types/profile';

const upload = <T>(path: string, file: File) => {
  const body = new FormData();
  body.append('file', file);
  return apiClient.request<T>(path, { method: 'POST', body });
};

export const profileApi = {
  get: () => apiClient.request<DeveloperProfile>('/api/v1/profile'),
  update: (profile: ProfileDraft) =>
    apiClient.request<DeveloperProfile>('/api/v1/profile', {
      method: 'PATCH',
      body: JSON.stringify(profile),
    }),
  uploadAvatar: (file: File) =>
    upload<DeveloperProfile>('/api/v1/profile/avatar', file),
  removeAvatar: () =>
    apiClient.request<DeveloperProfile>('/api/v1/profile/avatar', {
      method: 'DELETE',
    }),
  importCV: (file: File) =>
    upload<ProfileSuggestions>('/api/v1/profile/cv/import', file),
};
