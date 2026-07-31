from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    process_count: int
    active_process_count: int
    attempt_count: int
    completed_attempt_count: int
    evaluated_attempt_count: int
    average_score: int | None
    minimum_score: int | None
    maximum_score: int | None


class ScoreTrendPoint(BaseModel):
    attempt_id: str
    process_id: str
    process_title: str
    score: int = Field(ge=0, le=100)
    evaluated_at: str


class DashboardActivity(BaseModel):
    attempt_id: str
    process_id: str
    process_title: str
    stage_type: str
    attempt_number: int
    status: str
    score: int | None = Field(default=None, ge=0, le=100)
    occurred_at: str


class TopicFrequency(BaseModel):
    label: str
    count: int = Field(ge=1)


class OnboardingState(BaseModel):
    settings_configured: bool
    profile_completed: bool
    process_created: bool
    interview_started: bool


class Dashboard(BaseModel):
    stats: DashboardStats
    score_trend: list[ScoreTrendPoint]
    recent_activity: list[DashboardActivity]
    strengths: list[TopicFrequency]
    weaknesses: list[TopicFrequency]
    onboarding: OnboardingState
