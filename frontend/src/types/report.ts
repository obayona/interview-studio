export interface EvidenceReference {
  message_id: string;
  explanation: string;
}

export interface FeedbackItem {
  title: string;
  detail: string;
  evidence: EvidenceReference[];
}

export interface AnswerObservation {
  message_id: string;
  score: number;
  observation: string;
  advice: string;
}

export interface StudyPlanItem {
  priority: number;
  topic: string;
  action: string;
}

export interface CompetencyScores {
  communication: number;
  technical_knowledge: number;
  problem_solving: number;
  confidence: number;
  answer_relevance: number;
}

export interface EvaluationReport {
  schema_version: string;
  evaluation_version: number;
  overall_score: number;
  summary: string;
  competencies: CompetencyScores;
  strengths: FeedbackItem[];
  improvements: FeedbackItem[];
  strong_topics: string[];
  weak_topics: string[];
  answer_observations: AnswerObservation[];
  advice: string[];
  study_plan: StudyPlanItem[];
}

export interface SourcedText {
  text: string;
  stage_id: string;
  stage_type: string;
  attempt_id: string;
  attempt_number: number;
}

export interface SelectedStageReport {
  stage_id: string;
  stage_type: string;
  attempt_id: string;
  attempt_number: number;
  overall_score: number;
}

export interface ProcessReport {
  process_id: string;
  process_title: string;
  overall_score: number;
  competencies: CompetencyScores;
  evaluated_stage_count: number;
  enabled_stage_count: number;
  selected_reports: SelectedStageReport[];
  strengths: SourcedText[];
  improvements: SourcedText[];
  weak_topics: SourcedText[];
  advice: SourcedText[];
  study_plan: SourcedText[];
}
