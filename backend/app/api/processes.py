from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request, Response, status

from backend.app.application.processes import ProcessService
from backend.app.domain.processes import (
    ImportPreview,
    ImportPreviewRequest,
    InterviewProcess,
    ProcessCreate,
    ProcessSummary,
    ProcessUpdate,
)

router = APIRouter(prefix="/api/v1/processes", tags=["processes"])


def service(request: Request) -> ProcessService:
    return cast(ProcessService, request.app.state.processes)


@router.get("")
async def list_processes(request: Request) -> list[ProcessSummary]:
    return await service(request).list()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_process(request: Request, payload: ProcessCreate) -> InterviewProcess:
    return await service(request).create(payload)


@router.post("/import-preview")
async def preview_import(request: Request, payload: ImportPreviewRequest) -> ImportPreview:
    return await service(request).preview(str(payload.url))


@router.get("/{process_id}")
async def get_process(request: Request, process_id: str) -> InterviewProcess:
    return await service(request).get(process_id)


@router.patch("/{process_id}")
async def update_process(
    request: Request, process_id: str, payload: ProcessUpdate
) -> InterviewProcess:
    return await service(request).update(process_id, payload)


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process(request: Request, process_id: str) -> Response:
    await service(request).delete(process_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{process_id}/stages/{stage_id}/attempts",
    status_code=status.HTTP_201_CREATED,
)
async def start_attempt(request: Request, process_id: str, stage_id: str) -> dict[str, object]:
    return await service(request).start_attempt(process_id, stage_id)
