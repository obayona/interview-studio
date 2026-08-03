import { apiClient } from './api-client';
import type {
  SystemDesignSession,
  WhiteboardScene,
  WhiteboardSnapshot,
} from '../types/system-design';

export const systemDesignApi = {
  get: (attemptId: string) =>
    apiClient.request<SystemDesignSession>(
      `/api/v1/system-design/${encodeURIComponent(attemptId)}`,
    ),

  save: (attemptId: string, scene: WhiteboardScene, expectedVersion: number) =>
    apiClient.request<SystemDesignSession>(
      `/api/v1/system-design/${encodeURIComponent(attemptId)}`,
      {
        method: 'PUT',
        body: JSON.stringify({
          scene,
          expected_version: expectedVersion,
        }),
      },
    ),

  snapshot: (
    attemptId: string,
    sceneVersion: number,
    image: Blob,
    reason: WhiteboardSnapshot['reason'],
  ) => {
    const body = new FormData();
    body.set('scene_version', String(sceneVersion));
    body.set('reason', reason);
    body.set('image', image, 'whiteboard.png');
    return apiClient.request<WhiteboardSnapshot>(
      `/api/v1/system-design/${encodeURIComponent(attemptId)}/snapshots`,
      { method: 'POST', body },
    );
  },
};
