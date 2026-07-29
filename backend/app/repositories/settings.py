from __future__ import annotations

from collections.abc import Iterable

from backend.app.core.database import SQLiteManager


class SettingsRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def get_many(self, keys: Iterable[str]) -> dict[str, str]:
        key_tuple = tuple(keys)
        if not key_tuple:
            return {}
        placeholders = ",".join("?" for _ in key_tuple)
        rows = await self._database.fetchall(
            f"SELECT key, value FROM settings WHERE key IN ({placeholders})",
            key_tuple,
        )
        return {str(row["key"]): str(row["value"]) for row in rows}
