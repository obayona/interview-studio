import type {
  InterviewType,
  StageConfiguration,
  StageInput,
} from '../../types/process';

export const stageLabels: Record<InterviewType, string> = {
  screening: 'Screening',
  behavioral: 'Behavioral',
  technical: 'Technical / experience',
  experience: 'Experience',
  system_design: 'System design',
  mixed: 'Mixed interview',
};

export const newStageConfiguration = (): StageConfiguration => ({
  difficulty: 'mid',
  interviewer_profile: 'tech_lead',
  user_instructions: '',
  language: 'English',
  topics: [],
  limits: {
    max_questions: 8,
    max_duration_minutes: 30,
    follow_up_questions_per_topic: 1,
  },
});

export const defaultStages = (): StageInput[] =>
  (
    [
      ['screening', true],
      ['behavioral', true],
      ['technical', true],
      ['system_design', false],
    ] as const
  ).map(([stage_type, enabled]) => ({
    id: crypto.randomUUID(),
    stage_type,
    enabled,
    configuration: newStageConfiguration(),
  }));
