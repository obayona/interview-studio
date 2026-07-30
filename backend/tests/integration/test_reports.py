from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path

import httpx
from fastapi import FastAPI
from langchain_core.messages import AIMessage, HumanMessage

from backend.app.application.reports import ReportService
from backend.app.core.config import AppConfig
from backend.app.domain.processes import ProcessCreate
from backend.app.infrastructure.json_codec import StrictJsonCodec
from backend.app.main import create_app
from backend.report_engine import EvaluationContext, EvaluationReport
from backend.tests.integration.helpers import prepare_database


def report(score: int, evidence_id: str = "user-1") -> EvaluationReport:
    return EvaluationReport.model_validate(
        {
            "overall_score": score,
            "summary": "A concise evidence-based summary.",
            "competencies": {
                "communication": score,
                "technical_knowledge": score,
                "problem_solving": score,
                "confidence": score,
                "answer_relevance": score,
            },
            "strengths": [
                {
                    "title": "Clear structure",
                    "detail": "The answer followed a logical sequence.",
                    "evidence": [
                        {
                            "message_id": evidence_id,
                            "explanation": "The candidate explained the decision.",
                        }
                    ],
                }
            ],
            "improvements": [
                {
                    "title": "More detail",
                    "detail": "Include measurable outcomes.",
                    "evidence": [
                        {
                            "message_id": evidence_id,
                            "explanation": "The answer omitted results.",
                        }
                    ],
                }
            ],
            "strong_topics": ["Communication"],
            "weak_topics": ["Metrics"],
            "answer_observations": [
                {
                    "message_id": evidence_id,
                    "score": score,
                    "observation": "Relevant answer.",
                    "advice": "Add a measurable result.",
                }
            ],
            "advice": ["Practice concise STAR answers."],
            "study_plan": [
                {
                    "priority": 1,
                    "topic": "Impact statements",
                    "action": "Rewrite two answers with metrics.",
                }
            ],
        }
    )


class QueueEvaluator:
    def __init__(self, scores: list[int]) -> None:
        self.scores = scores

    async def evaluate(self, context: EvaluationContext) -> EvaluationReport:
        return report(self.scores.pop(0), context.messages[-1].id)


def stage() -> dict[str, object]:
    return {
        "stage_type": "technical",
        "enabled": True,
        "configuration": {
            "difficulty": "senior",
            "interviewer_profile": "tech_lead",
            "language": "English",
            "topics": ["APIs"],
            "limits": {
                "max_questions": 4,
                "max_duration_minutes": 20,
                "follow_up_questions_per_topic": 1,
            },
        },
    }


async def add_transcript(app: FastAPI, attempt_id: str) -> None:
    database = app.state.database
    codec = StrictJsonCodec()
    async with database.transaction() as connection:
        now = "2026-07-30T00:00:00+00:00"
        connection.executemany(
            """
            INSERT INTO interview_messages (
                id, attempt_id, langgraph_message_id, sequence, role,
                message_type, content_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    f"{attempt_id}-assistant",
                    attempt_id,
                    "assistant-1",
                    0,
                    "assistant",
                    "ai",
                    codec.dumps_message(AIMessage(id="assistant-1", content="Tell me more.")),
                    now,
                ),
                (
                    f"{attempt_id}-user",
                    attempt_id,
                    "user-1",
                    1,
                    "human",
                    "human",
                    codec.dumps_message(HumanMessage(id="user-1", content="I built an API.")),
                    now,
                ),
            ],
        )


async def test_completed_attempt_evaluation_and_process_best_attempt(
    tmp_path: Path,
) -> None:
    config = AppConfig(
        database_path=tmp_path / "reports.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        await app.state.settings.update({"api_key": "test-key"})
        current: ReportService = app.state.reports
        app.state.reports = ReportService(
            current._repository,
            current._attempts,
            current._profiles,
            current._settings,
            evaluator=QueueEvaluator([60, 85]),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = (
                await client.post(
                    "/api/v1/processes",
                    json={
                        "title": "API role",
                        "target_role": "Backend engineer",
                        "job": {"kind": "text", "value": "Build APIs."},
                        "stages": [stage()],
                    },
                )
            ).json()
            process_id = created["id"]
            stage_id = created["stages"][0]["id"]
            attempts = [
                (
                    await client.post(f"/api/v1/processes/{process_id}/stages/{stage_id}/attempts")
                ).json()
                for _ in range(2)
            ]
            incomplete = await client.post(f"/api/v1/attempts/{attempts[0]['id']}/report")
            assert incomplete.status_code == 409

            for attempt in attempts:
                await add_transcript(app, attempt["id"])
                await app.state.attempts.mark_ended(attempt["id"], "explicit_end")
                evaluated = await client.post(f"/api/v1/attempts/{attempt['id']}/report")
                assert evaluated.status_code == 200

            existing = await client.get(f"/api/v1/attempts/{attempts[1]['id']}/report")
            assert existing.json()["overall_score"] == 85
            aggregate = await client.get(f"/api/v1/processes/{process_id}/report")
            body = aggregate.json()
            assert body["overall_score"] == 85
            assert body["evaluated_stage_count"] == 1
            assert body["enabled_stage_count"] == 1
            assert body["selected_reports"][0]["attempt_number"] == 2


class BlockingEvaluator:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def evaluate(self, context: EvaluationContext) -> EvaluationReport:
        self.started.set()
        await self.release.wait()
        return report(75, context.messages[-1].id)


async def test_duplicate_evaluation_is_rejected_and_cancellation_can_retry(
    tmp_path: Path,
) -> None:
    config = AppConfig(
        database_path=tmp_path / "report-lock.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        await app.state.settings.update({"api_key": "test-key"})
        process = await app.state.processes.create(
            ProcessCreate.model_validate(
                {
                    "title": "Lock test",
                    "target_role": "Engineer",
                    "job": {"kind": "text", "value": "Build software."},
                    "stages": [stage()],
                }
            )
        )
        attempt = await app.state.processes.start_attempt(process.id, process.stages[0].id)
        attempt_id = str(attempt["id"])
        await add_transcript(app, attempt_id)
        await app.state.attempts.mark_ended(attempt_id, "explicit_end")
        blocking = BlockingEvaluator()
        current: ReportService = app.state.reports
        service = ReportService(
            current._repository,
            current._attempts,
            current._profiles,
            current._settings,
            evaluator=blocking,
        )
        first = asyncio.create_task(service.evaluate(attempt_id))
        await blocking.started.wait()
        try:
            await service.evaluate(attempt_id)
        except Exception as error:
            assert getattr(error, "code", None) == "evaluation_in_progress"
        else:
            raise AssertionError("A simultaneous evaluation should be rejected")
        first.cancel()
        with suppress(asyncio.CancelledError):
            await first
        assert await current._repository.get(attempt_id) is None
        service._evaluator = QueueEvaluator([77])
        retried = await service.evaluate(attempt_id)
        assert retried.overall_score == 77
