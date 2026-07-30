from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"
EVALUATION_VERSION = 1


class EvidenceReference(BaseModel):
    message_id: str
    explanation: str = Field(min_length=1, max_length=500)


class FeedbackItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(min_length=1, max_length=1_000)
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=5)


class AnswerObservation(BaseModel):
    message_id: str
    score: int = Field(ge=0, le=100)
    observation: str = Field(min_length=1, max_length=1_000)
    advice: str = Field(min_length=1, max_length=1_000)


class StudyPlanItem(BaseModel):
    priority: int = Field(ge=1, le=10)
    topic: str = Field(min_length=1, max_length=200)
    action: str = Field(min_length=1, max_length=1_000)


class CompetencyScores(BaseModel):
    communication: int = Field(ge=0, le=100)
    technical_knowledge: int = Field(ge=0, le=100)
    problem_solving: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    answer_relevance: int = Field(ge=0, le=100)


class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_VERSION
    evaluation_version: int = EVALUATION_VERSION
    overall_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1, max_length=2_000)
    competencies: CompetencyScores
    strengths: list[FeedbackItem] = Field(min_length=1, max_length=10)
    improvements: list[FeedbackItem] = Field(min_length=1, max_length=10)
    strong_topics: list[str] = Field(default_factory=list, max_length=20)
    weak_topics: list[str] = Field(default_factory=list, max_length=20)
    answer_observations: list[AnswerObservation] = Field(default_factory=list, max_length=50)
    advice: list[str] = Field(min_length=1, max_length=20)
    study_plan: list[StudyPlanItem] = Field(min_length=1, max_length=12)


class EvaluationMessage(BaseModel):
    id: str
    role: str
    text: str


class EvaluationContext(BaseModel):
    attempt_id: str
    process_title: str
    company_name: str
    target_role: str
    stage_type: str
    difficulty: str
    configured_topics: list[str]
    job_listing: str
    company_info: str
    candidate_profile: dict[str, object]
    messages: list[EvaluationMessage] = Field(min_length=2)


class SourcedText(BaseModel):
    text: str
    stage_id: str
    stage_type: str
    attempt_id: str
    attempt_number: int


class SelectedStageReport(BaseModel):
    stage_id: str
    stage_type: str
    attempt_id: str
    attempt_number: int
    overall_score: int


class ProcessReport(BaseModel):
    process_id: str
    process_title: str
    overall_score: int = Field(ge=0, le=100)
    competencies: CompetencyScores
    evaluated_stage_count: int
    enabled_stage_count: int
    selected_reports: list[SelectedStageReport]
    strengths: list[SourcedText]
    improvements: list[SourcedText]
    weak_topics: list[SourcedText]
    advice: list[SourcedText]
    study_plan: list[SourcedText]
