from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


def new_id() -> str:
    return str(uuid4())


class ProfileLink(BaseModel):
    id: str = Field(default_factory=new_id)
    link_type: Literal["linkedin", "portfolio", "other"]
    url: HttpUrl
    position: int = Field(default=0, ge=0)


class WorkExperience(BaseModel):
    id: str = Field(default_factory=new_id)
    employer: str = Field(default="", max_length=160)
    role: str = Field(default="", max_length=160)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str = Field(default="", max_length=5000)
    position: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_dates(self) -> WorkExperience:
        if self.is_current and self.end_date is not None:
            raise ValueError("A current role cannot have an end date")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        return self


class ProfileProject(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str = Field(default="", max_length=200)
    role: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=5000)
    technologies: list[str] = Field(default_factory=list, max_length=50)
    url: HttpUrl | None = None
    repository_url: HttpUrl | None = None
    position: int = Field(default=0, ge=0)

    @field_validator("technologies")
    @classmethod
    def clean_technologies(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))


class DeveloperProfile(BaseModel):
    id: str = "default"
    full_name: str = Field(default="", max_length=160)
    headline: str = Field(default="", max_length=200)
    summary: str = Field(default="", max_length=5000)
    location: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=80)
    skills: list[str] = Field(default_factory=list, max_length=100)
    seniority: str = Field(default="", max_length=80)
    availability: str = Field(default="", max_length=160)
    links: list[ProfileLink] = Field(default_factory=list)
    experiences: list[WorkExperience] = Field(default_factory=list)
    projects: list[ProfileProject] = Field(default_factory=list)
    avatar_url: str | None = None
    created_at: str
    updated_at: str

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    headline: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    skills: list[str] | None = Field(default=None, max_length=100)
    seniority: str | None = Field(default=None, max_length=80)
    availability: str | None = Field(default=None, max_length=160)
    links: list[ProfileLink] | None = None
    experiences: list[WorkExperience] | None = None
    projects: list[ProfileProject] | None = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))


class ProfileSuggestions(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = Field(default_factory=list)
    experiences: list[WorkExperience] = Field(default_factory=list)
    projects: list[ProfileProject] = Field(default_factory=list)
