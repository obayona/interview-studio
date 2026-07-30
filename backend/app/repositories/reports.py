from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from backend.app.core.database import SQLiteManager
from backend.report_engine.models import (
    EVALUATION_VERSION,
    CompetencyScores,
    EvaluationReport,
    ProcessReport,
    SelectedStageReport,
    SourcedText,
)


class ReportRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def get(self, attempt_id: str) -> EvaluationReport | None:
        row = await self._database.fetchone(
            """
            SELECT report_json FROM interview_reports
            WHERE attempt_id = ? AND evaluation_version = ?
            """,
            (attempt_id, EVALUATION_VERSION),
        )
        return (
            None if row is None else EvaluationReport.model_validate_json(str(row["report_json"]))
        )

    async def save(
        self,
        attempt_id: str,
        report: EvaluationReport,
        model_name: str,
    ) -> EvaluationReport:
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO interview_reports (
                    id, attempt_id, evaluation_version, schema_version,
                    overall_score, report_json, model_name, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(attempt_id, evaluation_version) DO NOTHING
                """,
                (
                    str(uuid4()),
                    attempt_id,
                    report.evaluation_version,
                    report.schema_version,
                    report.overall_score,
                    report.model_dump_json(),
                    model_name,
                    timestamp,
                    timestamp,
                ),
            )
            row = connection.execute(
                """
                SELECT report_json FROM interview_reports
                WHERE attempt_id = ? AND evaluation_version = ?
                """,
                (attempt_id, EVALUATION_VERSION),
            ).fetchone()
            if row is None:
                raise RuntimeError("The evaluation report could not be persisted")
        return EvaluationReport.model_validate_json(str(row["report_json"]))

    async def process_report(self, process_id: str) -> ProcessReport | None:
        process = await self._database.fetchone(
            "SELECT title FROM interview_processes WHERE id = ?", (process_id,)
        )
        if process is None:
            return None
        stage_rows = await self._database.fetchall(
            """
            SELECT s.id AS stage_id, s.stage_type, s.position,
                   a.id AS attempt_id, a.attempt_number, r.report_json
            FROM interview_stages s
            LEFT JOIN interview_attempts a ON a.stage_id = s.id
            LEFT JOIN interview_reports r
              ON r.attempt_id = a.id AND r.evaluation_version = ?
            WHERE s.process_id = ? AND s.enabled = 1
            ORDER BY s.position, a.attempt_number
            """,
            (EVALUATION_VERSION, process_id),
        )
        enabled_stage_ids = {str(row["stage_id"]) for row in stage_rows}
        winners: dict[str, tuple[str, int, EvaluationReport, str]] = {}
        for row in stage_rows:
            if row["report_json"] is None:
                continue
            report = EvaluationReport.model_validate_json(str(row["report_json"]))
            stage_id = str(row["stage_id"])
            current = winners.get(stage_id)
            attempt_number = int(row["attempt_number"])
            if current is None or (report.overall_score, attempt_number) > (
                current[2].overall_score,
                current[1],
            ):
                winners[stage_id] = (
                    str(row["attempt_id"]),
                    attempt_number,
                    report,
                    str(row["stage_type"]),
                )
        if not winners:
            return None
        ordered = [(stage_id, *winner) for stage_id, winner in winners.items()]
        reports = [item[3] for item in ordered]
        return ProcessReport(
            process_id=process_id,
            process_title=str(process["title"]),
            overall_score=_average([report.overall_score for report in reports]),
            competencies=CompetencyScores(
                communication=_average([report.competencies.communication for report in reports]),
                technical_knowledge=_average(
                    [report.competencies.technical_knowledge for report in reports]
                ),
                problem_solving=_average(
                    [report.competencies.problem_solving for report in reports]
                ),
                confidence=_average([report.competencies.confidence for report in reports]),
                answer_relevance=_average(
                    [report.competencies.answer_relevance for report in reports]
                ),
            ),
            evaluated_stage_count=len(winners),
            enabled_stage_count=len(enabled_stage_ids),
            selected_reports=[
                SelectedStageReport(
                    stage_id=stage_id,
                    stage_type=stage_type,
                    attempt_id=attempt_id,
                    attempt_number=attempt_number,
                    overall_score=report.overall_score,
                )
                for stage_id, attempt_id, attempt_number, report, stage_type in ordered
            ],
            strengths=_merge_items(ordered, "strengths"),
            improvements=_merge_items(ordered, "improvements"),
            weak_topics=_merge_items(ordered, "weak_topics"),
            advice=_merge_items(ordered, "advice"),
            study_plan=_merge_items(ordered, "study_plan"),
        )


def _average(values: list[int]) -> int:
    return round(sum(values) / len(values))


def _merge_items(
    reports: list[tuple[str, str, int, EvaluationReport, str]],
    field: str,
) -> list[SourcedText]:
    result: list[SourcedText] = []
    seen: set[str] = set()
    for stage_id, attempt_id, attempt_number, report, stage_type in reports:
        values = getattr(report, field)
        for value in values:
            if field in {"strengths", "improvements"}:
                text = f"{value.title}: {value.detail}"
            elif field == "study_plan":
                text = f"{value.topic}: {value.action}"
            else:
                text = str(value)
            key = " ".join(text.casefold().split())
            if key in seen:
                continue
            seen.add(key)
            result.append(
                SourcedText(
                    text=text,
                    stage_id=stage_id,
                    stage_type=stage_type,
                    attempt_id=attempt_id,
                    attempt_number=attempt_number,
                )
            )
    return result
