from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class InterviewType(StrEnum):
    SCREENING = "screening"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    EXPERIENCE = "experience"
    SYSTEM_DESIGN = "system_design"
    MIXED = "mixed"


class InterviewerProfile(StrEnum):
    HR_RECRUITER = "hr_recruiter"
    TECH_LEAD = "tech_lead"
    ENGINEERING_MANAGER = "engineering_manager"
    CEO = "ceo"
    CTO = "cto"
    PEER_ENGINEER = "peer_engineer"


class DifficultyLevel(StrEnum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"


class TerminationReason(StrEnum):
    QUESTION_LIMIT = "question_limit"
    TIME_LIMIT = "time_limit"
    TOPICS_COVERED = "topics_covered"
    USER_REQUESTED = "user_requested"


class CandidateProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(default="Candidate", min_length=1, max_length=120)
    headline: str = Field(default="", max_length=240)
    summary: str = Field(default="", max_length=8_000)
    skills: tuple[str, ...] = ()
    years_experience: float | None = Field(default=None, ge=0, le=80)
    portfolio_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, skills: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(skill.strip() for skill in skills if skill.strip()))


class InterviewLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_questions: int = Field(default=8, ge=1, le=100)
    max_duration_minutes: int = Field(default=30, ge=1, le=240)
    follow_up_questions_per_topic: int = Field(default=1, ge=0, le=3)


class MediaCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    text_input: bool = True
    text_output: bool = True
    speech_to_text: bool = False
    text_to_speech: bool = False
    natural_interruptions: bool = False


class InterviewConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate: CandidateProfile = Field(default_factory=CandidateProfile)
    job_listing: str = Field(min_length=1, max_length=50_000)
    company_info: str = Field(default="", max_length=30_000)
    interview_type: InterviewType = InterviewType.MIXED
    interviewer_profile: InterviewerProfile = InterviewerProfile.TECH_LEAD
    difficulty: DifficultyLevel = DifficultyLevel.MID
    user_instructions: str = Field(default="", max_length=4_000)
    language: str = Field(default="English", min_length=2, max_length=80)
    topics: tuple[str, ...] = ()
    limits: InterviewLimits = Field(default_factory=InterviewLimits)
    media: MediaCapabilities = Field(default_factory=MediaCapabilities)

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, topics: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(topic.strip() for topic in topics if topic.strip()))
