export type WhiteboardScene = {
  type?: string;
  version?: number;
  source?: string;
  elements: unknown[];
  appState: Record<string, unknown>;
  files: Record<string, unknown>;
};

export type WhiteboardSnapshot = {
  id: string;
  scene_version: number;
  reason: 'periodic' | 'explicit' | 'interview_end';
  created_at: string;
  image_url: string;
};

export type SystemDesignSession = {
  attempt_id: string;
  scene: WhiteboardScene;
  scene_version: number;
  created_at?: string;
  updated_at?: string;
  snapshots: WhiteboardSnapshot[];
};
