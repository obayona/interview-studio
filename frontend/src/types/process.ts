export type InterviewType =
  | 'screening'
  | 'behavioral'
  | 'technical'
  | 'experience'
  | 'system_design'
  | 'mixed';

export type Difficulty = 'junior' | 'mid' | 'senior' | 'staff';
export type Interviewer =
  | 'hr_recruiter'
  | 'tech_lead'
  | 'engineering_manager'
  | 'ceo'
  | 'cto'
  | 'peer_engineer';

export interface StageConfiguration {
  difficulty: Difficulty;
  interviewer_profile: Interviewer;
  user_instructions: string;
  language: string;
  topics: string[];
  limits: {
    max_questions: number;
    max_duration_minutes: number;
    follow_up_questions_per_topic: number;
  };
  media: {
    text_input: boolean;
    text_output: boolean;
    speech_to_text: boolean;
    text_to_speech: boolean;
    natural_interruptions: boolean;
  };
}

export interface StageInput {
  id: string;
  stage_type: InterviewType;
  enabled: boolean;
  configuration: StageConfiguration;
}

export interface AttemptSummary {
  id: string;
  attempt_number: number;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  termination_reason: string | null;
  created_at: string;
}

export interface ProcessStage extends StageInput {
  position: number;
  status: string;
  attempts: AttemptSummary[];
}

export interface InterviewProcess {
  id: string;
  title: string;
  company_name: string;
  target_role: string;
  job_description: string;
  company_info: string;
  job_source_url: string | null;
  company_source_url: string | null;
  status: string;
  stages: ProcessStage[];
  created_at: string;
  updated_at: string;
}

export interface ProcessSummary {
  id: string;
  title: string;
  company_name: string;
  target_role: string;
  status: string;
  stage_count: number;
  completed_stage_count: number;
  attempt_count: number;
  updated_at: string;
}

export interface ContentSource {
  kind: 'text' | 'url';
  value: string;
}

export interface ProcessDraft {
  title: string;
  company_name: string;
  target_role: string;
  job: ContentSource;
  company: ContentSource | null;
  stages: StageInput[];
}
