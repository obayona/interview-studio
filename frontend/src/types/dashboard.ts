export interface DashboardStats {
  process_count: number;
  active_process_count: number;
  attempt_count: number;
  completed_attempt_count: number;
  evaluated_attempt_count: number;
  average_score: number | null;
  minimum_score: number | null;
  maximum_score: number | null;
}

export interface ScoreTrendPoint {
  attempt_id: string;
  process_id: string;
  process_title: string;
  score: number;
  evaluated_at: string;
}

export interface DashboardActivity {
  attempt_id: string;
  process_id: string;
  process_title: string;
  stage_type: string;
  attempt_number: number;
  status: string;
  score: number | null;
  occurred_at: string;
}

export interface TopicFrequency {
  label: string;
  count: number;
}

export interface DashboardData {
  stats: DashboardStats;
  score_trend: ScoreTrendPoint[];
  recent_activity: DashboardActivity[];
  strengths: TopicFrequency[];
  weaknesses: TopicFrequency[];
  onboarding: {
    settings_configured: boolean;
    profile_completed: boolean;
    process_created: boolean;
    interview_started: boolean;
  };
}
