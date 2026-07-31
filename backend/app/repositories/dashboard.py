from __future__ import annotations

import sqlite3
from collections import Counter

from backend.app.core.database import SQLiteManager
from backend.app.domain.dashboard import (
    Dashboard,
    DashboardActivity,
    DashboardStats,
    OnboardingState,
    ScoreTrendPoint,
    TopicFrequency,
)
from backend.report_engine import EvaluationReport


class DashboardRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def get(self, *, settings_configured: bool) -> Dashboard:
        counts = await self._database.fetchone(
            """
            SELECT
              (SELECT COUNT(*) FROM interview_processes) AS process_count,
              (SELECT COUNT(*) FROM interview_processes WHERE status = 'active')
                AS active_process_count,
              (SELECT COUNT(*) FROM interview_attempts WHERE stage_id IS NOT NULL)
                AS attempt_count,
              (SELECT COUNT(*) FROM interview_attempts
                 WHERE stage_id IS NOT NULL AND status = 'completed')
                AS completed_attempt_count,
              (SELECT COUNT(*) FROM interview_reports) AS evaluated_attempt_count,
              (SELECT ROUND(AVG(overall_score)) FROM interview_reports) AS average_score,
              (SELECT MIN(overall_score) FROM interview_reports) AS minimum_score,
              (SELECT MAX(overall_score) FROM interview_reports) AS maximum_score
            """
        )
        if counts is None:
            raise RuntimeError("Dashboard aggregates could not be loaded")
        trend_rows = await self._database.fetchall(
            """
            SELECT a.id AS attempt_id, p.id AS process_id, p.title AS process_title,
                   r.overall_score, r.created_at
            FROM interview_reports r
            JOIN interview_attempts a ON a.id = r.attempt_id
            JOIN interview_stages s ON s.id = a.stage_id
            JOIN interview_processes p ON p.id = s.process_id
            ORDER BY r.created_at, r.id
            """
        )
        activity_rows = await self._database.fetchall(
            """
            SELECT a.id AS attempt_id, p.id AS process_id, p.title AS process_title,
                   s.stage_type, a.attempt_number, a.status, r.overall_score,
                   COALESCE(r.updated_at, a.updated_at) AS occurred_at
            FROM interview_attempts a
            JOIN interview_stages s ON s.id = a.stage_id
            JOIN interview_processes p ON p.id = s.process_id
            LEFT JOIN interview_reports r ON r.attempt_id = a.id
            ORDER BY occurred_at DESC, a.id DESC
            LIMIT 8
            """
        )
        report_rows = await self._database.fetchall(
            "SELECT report_json FROM interview_reports ORDER BY created_at DESC"
        )
        profile = await self._database.fetchone(
            """
            SELECT full_name, headline, summary, skills_json
            FROM developer_profiles WHERE id = 'default'
            """
        )
        strengths: Counter[str] = Counter()
        weaknesses: Counter[str] = Counter()
        for row in report_rows:
            report = EvaluationReport.model_validate_json(str(row["report_json"]))
            strengths.update(_normalized_topics(report.strong_topics))
            weaknesses.update(_normalized_topics(report.weak_topics))
        attempt_count = int(counts["attempt_count"])
        process_count = int(counts["process_count"])
        return Dashboard(
            stats=DashboardStats(
                process_count=process_count,
                active_process_count=int(counts["active_process_count"]),
                attempt_count=attempt_count,
                completed_attempt_count=int(counts["completed_attempt_count"]),
                evaluated_attempt_count=int(counts["evaluated_attempt_count"]),
                average_score=_optional_int(counts["average_score"]),
                minimum_score=_optional_int(counts["minimum_score"]),
                maximum_score=_optional_int(counts["maximum_score"]),
            ),
            score_trend=[
                ScoreTrendPoint(
                    attempt_id=str(row["attempt_id"]),
                    process_id=str(row["process_id"]),
                    process_title=str(row["process_title"]),
                    score=int(row["overall_score"]),
                    evaluated_at=str(row["created_at"]),
                )
                for row in trend_rows
            ],
            recent_activity=[
                DashboardActivity(
                    attempt_id=str(row["attempt_id"]),
                    process_id=str(row["process_id"]),
                    process_title=str(row["process_title"]),
                    stage_type=str(row["stage_type"]),
                    attempt_number=int(row["attempt_number"]),
                    status=str(row["status"]),
                    score=_optional_int(row["overall_score"]),
                    occurred_at=str(row["occurred_at"]),
                )
                for row in activity_rows
            ],
            strengths=_frequencies(strengths),
            weaknesses=_frequencies(weaknesses),
            onboarding=OnboardingState(
                settings_configured=settings_configured,
                profile_completed=_profile_completed(profile),
                process_created=process_count > 0,
                interview_started=attempt_count > 0,
            ),
        )


def _optional_int(value: object) -> int | None:
    return None if value is None else round(float(str(value)))


def _normalized_topics(values: list[str]) -> list[str]:
    return [" ".join(value.split()) for value in values if value.strip()]


def _frequencies(counter: Counter[str]) -> list[TopicFrequency]:
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold()))
    return [TopicFrequency(label=label, count=count) for label, count in ordered[:5]]


def _profile_completed(row: sqlite3.Row | None) -> bool:
    if row is None:
        return False
    return bool(
        str(row["full_name"]).strip()
        and str(row["headline"]).strip()
        and str(row["summary"]).strip()
        and str(row["skills_json"]).strip() not in {"", "[]"}
    )
