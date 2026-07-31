from __future__ import annotations

from backend.app.core.config import SettingsService
from backend.app.domain.dashboard import Dashboard
from backend.app.repositories.dashboard import DashboardRepository


class DashboardService:
    def __init__(self, repository: DashboardRepository, settings: SettingsService) -> None:
        self._repository = repository
        self._settings = settings

    async def get(self) -> Dashboard:
        ai = await self._settings.ai()
        return await self._repository.get(settings_configured=bool(ai.api_key))
