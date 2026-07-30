from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol

from backend.app.core.config import SettingsService
from backend.app.core.errors import ApplicationError, AttemptNotFoundError
from backend.app.repositories.attempts import AttemptRepository
from backend.app.repositories.profile import ProfileRepository
from backend.app.repositories.reports import ReportRepository
from backend.report_engine import (
    EvaluationContext,
    EvaluationReport,
    ProcessReport,
    ReportEngine,
)
from backend.report_engine.models import EvaluationMessage


class Evaluator(Protocol):
    async def evaluate(self, context: EvaluationContext) -> EvaluationReport: ...


EvaluatorFactory = Callable[[str, str], Evaluator]


class ReportService:
    def __init__(
        self,
        repository: ReportRepository,
        attempts: AttemptRepository,
        profiles: ProfileRepository,
        settings: SettingsService,
        *,
        evaluator: Evaluator | None = None,
        evaluator_factory: EvaluatorFactory = ReportEngine.from_openai,
    ) -> None:
        self._repository = repository
        self._attempts = attempts
        self._profiles = profiles
        self._settings = settings
        self._evaluator = evaluator
        self._evaluator_factory = evaluator_factory
        self._active: set[str] = set()
        self._guard = asyncio.Lock()

    async def get(self, attempt_id: str) -> EvaluationReport:
        if await self._attempts.status(attempt_id) is None:
            raise AttemptNotFoundError(attempt_id)
        report = await self._repository.get(attempt_id)
        if report is None:
            raise ApplicationError(
                code="report_not_found",
                message="This interview attempt has not been evaluated.",
                status_code=404,
            )
        return report

    async def evaluate(self, attempt_id: str) -> EvaluationReport:
        status = await self._attempts.status(attempt_id)
        if status is None:
            raise AttemptNotFoundError(attempt_id)
        if status != "completed":
            raise ApplicationError(
                code="attempt_not_completed",
                message="Only completed interview attempts can be evaluated.",
                status_code=409,
            )
        existing = await self._repository.get(attempt_id)
        if existing is not None:
            return existing
        async with self._guard:
            if attempt_id in self._active:
                raise ApplicationError(
                    code="evaluation_in_progress",
                    message="This interview attempt is already being evaluated.",
                    status_code=409,
                )
            self._active.add(attempt_id)
        try:
            transcript = await self._attempts.transcript(attempt_id)
            context = await self._attempts.context(attempt_id)
            if context is None:
                raise AttemptNotFoundError(attempt_id)
            profile = await self._profiles.get()
            ai = await self._settings.ai()
            if not ai.interview_ready:
                raise ApplicationError(
                    code="provider_not_configured",
                    message="Configure an OpenAI API key before evaluating an interview.",
                    status_code=503,
                )
            evaluation_context = EvaluationContext(
                attempt_id=attempt_id,
                process_title=context["process_title"],
                company_name=context["company_name"],
                target_role=context["target_role"],
                stage_type=context["stage_type"],
                difficulty=context["difficulty"],
                configured_topics=context["configured_topics"],
                job_listing=context["job_listing"],
                company_info=context["company_info"],
                candidate_profile=profile.model_dump(mode="json"),
                messages=[
                    EvaluationMessage(id=item["id"], role=item["role"], text=item["text"])
                    for item in transcript
                ],
            )
            evaluator = self._evaluator or self._evaluator_factory(ai.api_key, ai.chat_model)
            try:
                report = await evaluator.evaluate(evaluation_context)
                self._validate_evidence(report, evaluation_context)
            except ApplicationError:
                raise
            except Exception as error:
                raise ApplicationError(
                    code="evaluation_failed",
                    message="The interview could not be evaluated by the AI provider.",
                    status_code=502,
                ) from error
            return await self._repository.save(attempt_id, report, ai.chat_model)
        finally:
            async with self._guard:
                self._active.discard(attempt_id)

    async def process_report(self, process_id: str) -> ProcessReport:
        report = await self._repository.process_report(process_id)
        if report is None:
            raise ApplicationError(
                code="process_report_not_found",
                message="No evaluated attempts are available for this process.",
                status_code=404,
            )
        return report

    @staticmethod
    def _validate_evidence(report: EvaluationReport, context: EvaluationContext) -> None:
        known_ids = {message.id for message in context.messages}
        referenced_ids = {
            evidence.message_id
            for item in (*report.strengths, *report.improvements)
            for evidence in item.evidence
        }
        referenced_ids.update(observation.message_id for observation in report.answer_observations)
        unknown = referenced_ids - known_ids
        if unknown:
            raise ValueError(f"Report references unknown transcript messages: {sorted(unknown)}")
