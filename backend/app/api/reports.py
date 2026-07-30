from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from backend.app.application.reports import ReportService
from backend.report_engine import EvaluationReport, ProcessReport

router = APIRouter(prefix="/api/v1", tags=["reports"])


def service(request: Request) -> ReportService:
    return cast(ReportService, request.app.state.reports)


@router.get("/attempts/{attempt_id}/report")
async def get_attempt_report(request: Request, attempt_id: str) -> EvaluationReport:
    return await service(request).get(attempt_id)


@router.post("/attempts/{attempt_id}/report")
async def evaluate_attempt(request: Request, attempt_id: str) -> EvaluationReport:
    return await service(request).evaluate(attempt_id)


@router.get("/processes/{process_id}/report")
async def get_process_report(request: Request, process_id: str) -> ProcessReport:
    return await service(request).process_report(process_id)
