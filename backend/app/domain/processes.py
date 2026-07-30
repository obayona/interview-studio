from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, model_validator

from backend.interview_engine.models import (
    DifficultyLevel,
    InterviewerProfile,
    InterviewLimits,
    InterviewType,
)


def new_id() -> str:
    return str(uuid4())


class ContentSource(BaseModel):
    kind: Literal["text", "url"] = "text"
    value: str = Field(min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def validate_url(self) -> ContentSource:
        if self.kind == "url":
            HttpUrl(self.value)
        return self


class StageConfiguration(BaseModel):
    difficulty: DifficultyLevel = DifficultyLevel.MID
    interviewer_profile: InterviewerProfile = InterviewerProfile.TECH_LEAD
    user_instructions: str = Field(default="", max_length=4_000)
    language: str = Field(default="English", min_length=2, max_length=80)
    topics: list[str] = Field(default_factory=list, max_length=50)
    limits: InterviewLimits = Field(default_factory=InterviewLimits)


class StageInput(BaseModel):
    id: str = Field(default_factory=new_id)
    stage_type: InterviewType
    enabled: bool = True
    configuration: StageConfiguration = Field(default_factory=StageConfiguration)


class ProcessCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company_name: str = Field(default="", max_length=200)
    target_role: str = Field(min_length=1, max_length=200)
    job: ContentSource
    company: ContentSource | None = None
    stages: list[StageInput] = Field(min_length=1, max_length=12)


class ProcessUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    target_role: str | None = Field(default=None, min_length=1, max_length=200)
    status: Literal["active", "completed", "archived"] | None = None
    job: ContentSource | None = None
    company: ContentSource | None = None
    stages: list[StageInput] | None = Field(default=None, min_length=1, max_length=12)


class AttemptSummary(BaseModel):
    id: str
    attempt_number: int
    status: str
    started_at: str | None
    ended_at: str | None
    termination_reason: str | None
    report_available: bool = False
    overall_score: int | None = None
    created_at: str


class ProcessStage(BaseModel):
    id: str
    stage_type: InterviewType
    position: int
    enabled: bool
    status: str
    configuration: StageConfiguration
    attempts: list[AttemptSummary] = Field(default_factory=list)


class InterviewProcess(BaseModel):
    id: str
    title: str
    company_name: str
    target_role: str
    job_description: str
    company_info: str
    job_source_url: str | None
    company_source_url: str | None
    status: str
    stages: list[ProcessStage]
    created_at: str
    updated_at: str


class ProcessSummary(BaseModel):
    id: str
    title: str
    company_name: str
    target_role: str
    status: str
    stage_count: int
    completed_stage_count: int
    attempt_count: int
    updated_at: str


class ImportPreviewRequest(BaseModel):
    url: HttpUrl


class ImportPreview(BaseModel):
    url: str
    content: str
