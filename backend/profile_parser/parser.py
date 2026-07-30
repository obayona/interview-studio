from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import TypedDict, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, SecretStr
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.app.domain.profile import (
    ProfileProject,
    ProfileSuggestions,
    WorkExperience,
)

MAX_PDF_PAGES = 30
MAX_EXTRACTED_CHARACTERS = 200_000

SYSTEM_PROMPT = """You extract a developer profile from resume text.

Use only facts explicitly present in the resume. Do not infer a location, phone number,
dates, projects, job titles, employers, or technologies that are not stated.

Interpret layout carefully:
- A professional title near the candidate name is the headline.
- The summary must come from the resume's summary/profile text, not from job history.
- Each work-experience item must keep the exact employer, role, dates, and its own duties.
- A current role has is_current=true and end_date=null.
- Convert month/year dates to the first day of that month and year-only dates to January 1.
- Publications, education, and generic expertise are not projects.
- Put concrete technologies and professional competencies in skills without duplicates.
- Use null or an empty list when the resume does not provide a field.

Return work experience and projects in the order shown in the resume."""


class ExperienceExtraction(BaseModel):
    employer: str
    role: str
    start_date: date | None
    end_date: date | None
    is_current: bool
    description: str


class ProjectExtraction(BaseModel):
    name: str
    role: str
    description: str
    technologies: list[str]
    url: str | None
    repository_url: str | None


class ProfileExtraction(BaseModel):
    full_name: str | None
    headline: str | None
    summary: str | None
    location: str | None
    email: str | None
    phone: str | None
    skills: list[str] = Field(max_length=100)
    experiences: list[ExperienceExtraction] = Field(max_length=20)
    projects: list[ProjectExtraction] = Field(max_length=20)


class ParserState(TypedDict):
    text: str
    extraction: ProfileExtraction | None


class PDFTextExtractor:
    """Converts a bounded, text-based PDF into plain text."""

    def extract(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("Password-protected PDFs are not supported")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise ValueError(f"PDFs may contain at most {MAX_PDF_PAGES} pages")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as error:
            raise ValueError("The PDF could not be read") from error
        text = text.replace("\x00", "").strip()
        if not text:
            raise ValueError("The PDF does not contain extractable text")
        return text[:MAX_EXTRACTED_CHARACTERS]


class CVParser:
    """Uses a LangGraph workflow for AI resume extraction."""

    def __init__(self, model: BaseChatModel) -> None:
        self._structured_model = cast(
            Runnable[object, object],
            model.with_structured_output(ProfileExtraction, method="json_schema"),
        )
        graph = StateGraph(ParserState)
        graph.add_node("extract_profile", self._extract_profile)
        graph.add_edge(START, "extract_profile")
        graph.add_edge("extract_profile", END)
        self._graph = graph.compile()

    @classmethod
    def from_openai(cls, api_key: str, model_name: str) -> CVParser:

        return cls(
            ChatOpenAI(
                api_key=SecretStr(api_key),
                model=model_name,
                temperature=0,
                timeout=30,
                max_retries=1,
            )
        )

    async def parse(self, text: str) -> ProfileSuggestions:
        result = await self._graph.ainvoke({"text": text, "extraction": None})
        extraction = result["extraction"]
        if extraction is None:
            raise ValueError("The AI did not return a profile")
        return self._to_suggestions(extraction)

    async def _extract_profile(self, state: ParserState) -> dict[str, ProfileExtraction]:
        result = await self._structured_model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"<resume>\n{state['text']}\n</resume>"),
            ]
        )
        return {"extraction": ProfileExtraction.model_validate(result)}

    def _to_suggestions(self, extraction: ProfileExtraction) -> ProfileSuggestions:
        return ProfileSuggestions(
            full_name=extraction.full_name,
            headline=extraction.headline,
            summary=extraction.summary,
            location=extraction.location,
            email=extraction.email,
            phone=extraction.phone,
            skills=extraction.skills,
            experiences=[
                WorkExperience(
                    employer=item.employer,
                    role=item.role,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    is_current=item.is_current and item.end_date is None,
                    description=item.description,
                    position=position,
                )
                for position, item in enumerate(extraction.experiences)
            ],
            projects=[
                ProfileProject.model_validate(
                    {
                        **item.model_dump(),
                        "position": position,
                    }
                )
                for position, item in enumerate(extraction.projects)
            ],
        )
