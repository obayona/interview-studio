from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.interviews import attempts_router
from backend.app.api.interviews import router as interviews_router
from backend.app.api.processes import router as processes_router
from backend.app.api.profile import router as profile_router
from backend.app.api.reports import router as reports_router
from backend.app.api.settings import router as settings_router
from backend.app.api.system_design import router as system_design_router
from backend.app.api.websocket import router as websocket_router
from backend.app.application.dashboard import DashboardService
from backend.app.application.interviews import InterviewService
from backend.app.application.processes import ProcessService
from backend.app.application.profiles import ProfileService
from backend.app.application.reports import ReportService
from backend.app.application.system_design import SystemDesignService
from backend.app.core.config import AppConfig, SettingsService
from backend.app.core.database import SQLiteManager
from backend.app.core.errors import ApplicationError
from backend.app.core.secrets import SecretBox
from backend.app.infrastructure.checkpointer import InterviewSQLiteCheckpointer
from backend.app.repositories.attempts import AttemptRepository
from backend.app.repositories.dashboard import DashboardRepository
from backend.app.repositories.processes import ProcessRepository
from backend.app.repositories.profile import ProfileRepository
from backend.app.repositories.reports import ReportRepository
from backend.app.repositories.settings import SettingsRepository
from backend.app.repositories.system_design import SystemDesignRepository


def create_app(config: AppConfig | None = None) -> FastAPI:
    application_config = config or AppConfig.default()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logging.getLogger("interview-studio").debug("Starting application")
        database = SQLiteManager(
            application_config.database_path, application_config.migrations_path
        )
        await database.start()
        secret_path = application_config.secret_path or application_config.database_path.with_name(
            ".secret-key"
        )
        settings_repository = SettingsRepository(database, SecretBox(secret_path))
        settings = SettingsService(settings_repository)
        attempts = AttemptRepository(database)
        profiles = ProfileRepository(database)
        checkpointer = InterviewSQLiteCheckpointer(database)
        app.state.database = database
        app.state.settings = settings
        app.state.attempts = attempts
        app.state.interviews = InterviewService(attempts, settings, checkpointer)
        app.state.profile = ProfileService(profiles, settings)
        app.state.processes = ProcessService(ProcessRepository(database), profiles, settings)
        app.state.reports = ReportService(ReportRepository(database), attempts, profiles, settings)
        app.state.dashboard = DashboardService(DashboardRepository(database), settings)
        app.state.system_design = SystemDesignService(SystemDesignRepository(database))
        yield
        await database.close()

    app = FastAPI(title="Interview Studio", version="0.2.0", lifespan=lifespan)
    app.include_router(interviews_router)
    app.include_router(dashboard_router)
    app.include_router(attempts_router)
    app.include_router(profile_router)
    app.include_router(processes_router)
    app.include_router(reports_router)
    app.include_router(settings_router)
    app.include_router(system_design_router)
    app.include_router(websocket_router)

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, error: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "code": error.code,
                "message": error.message,
                "field_errors": error.field_errors,
                "request_id": request.state.request_id,
            },
        )

    @app.get("/")
    async def index() -> dict[str, str]:
        return {
            "name": "Interview Studio API",
            "health": "/health/ready",
            "docs": "/docs",
        }

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready(request: Request) -> dict[str, str]:
        await request.app.state.database.fetchone("SELECT 1")
        return {"status": "ready"}

    @app.get("/api/v1/capabilities")
    async def capabilities(request: Request) -> dict[str, object]:
        store = cast(SettingsService, request.app.state.settings)
        return await store.capabilities()

    return app


app = create_app()
