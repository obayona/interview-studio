import { apiClient } from './api-client';

export interface TranscriptMessage {
  id: string;
  sequence: number;
  role: 'user' | 'assistant';
  text: string;
  created_at: string;
}

export interface InterviewContext {
  process_title: string;
  company_name: string;
  target_role: string;
  stage_type: string;
  attempt_number: number;
  company_info: string;
  job_listing: string;
  difficulty: string;
  interviewer_profile: string;
  language: string;
  configured_topics: string[];
  topics_covered: string[];
  max_questions: number;
  max_duration_minutes: number;
}

export const interviewApi = {
  history: (attemptId: string) =>
    apiClient.request<{
      attempt_id: string;
      status: string;
      context: InterviewContext;
      messages: TranscriptMessage[];
    }>(`/api/v1/interviews/${encodeURIComponent(attemptId)}/history`),
};
