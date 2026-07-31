from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from backend.app.application.dashboard import DashboardService
from backend.app.domain.dashboard import Dashboard

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(request: Request) -> Dashboard:
    service = cast(DashboardService, request.app.state.dashboard)
    return await service.get()
