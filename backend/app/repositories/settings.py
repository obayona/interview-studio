from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from backend.app.core.database import SQLiteManager
from backend.app.core.secrets import SecretBox
from backend.app.core.settings_definitions import SETTING_DEFINITIONS, SettingKey, setting_keys


class SettingsRepository:
    def __init__(self, database: SQLiteManager, secrets: SecretBox) -> None:
        self._database = database
        self._secrets = secrets

    async def get_many(self, keys: Iterable[str]) -> dict[str, str]:
        key_tuple = tuple(keys)
        if not key_tuple:
            return {}
        placeholders = ",".join("?" for _ in key_tuple)
        rows = await self._database.fetchall(
            f"SELECT key, value FROM settings WHERE key IN ({placeholders})",
            key_tuple,
        )
        result: dict[str, str] = {}
        for row in rows:
            key = str(row["key"])
            value = str(row["value"])
            try:
                definition = SETTING_DEFINITIONS.get(SettingKey(key))
            except ValueError:
                definition = None
            result[key] = (
                self._secrets.decrypt(value) if definition and definition.secret else value
            )
        return result

    async def status(self) -> list[dict[str, object]]:
        rows = await self._database.fetchall(
            "SELECT key, value, is_secret, updated_at FROM settings ORDER BY key"
        )
        configured: dict[str, dict[str, object]] = {}
        for row in rows:
            key = str(row["key"])
            value = str(row["value"])
            if bool(row["is_secret"]):
                try:
                    plaintext = self._secrets.decrypt(value)
                except ValueError:
                    plaintext = ""
                configured[key] = {
                    "configured": bool(plaintext),
                    "masked_suffix": plaintext[-4:] if plaintext else None,
                    "updated_at": str(row["updated_at"]),
                }
            else:
                configured[key] = {
                    "configured": bool(value),
                    "value": value,
                    "updated_at": str(row["updated_at"]),
                }
        return [
            {
                "key": key.value,
                **configured.get(
                    key.value,
                    {"configured": False, "value": definition.default or None},
                ),
            }
            for key, definition in SETTING_DEFINITIONS.items()
        ]

    async def set_many(self, values: dict[str, str]) -> None:
        unknown = set(values) - set(setting_keys())
        if unknown:
            raise ValueError(f"Unknown settings: {', '.join(sorted(unknown))}")
        now = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            for key, value in values.items():
                definition = SETTING_DEFINITIONS[SettingKey(key)]
                stored = self._secrets.encrypt(value) if definition.secret else value
                connection.execute(
                    """
                    INSERT INTO settings(key, value, is_secret, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                        is_secret=excluded.is_secret, updated_at=excluded.updated_at
                    """,
                    (key, stored, int(definition.secret), now, now),
                )

    async def remove(self, key: str) -> None:
        if key not in setting_keys():
            raise ValueError(f"Unknown setting: {key}")
        async with self._database.transaction() as connection:
            connection.execute("DELETE FROM settings WHERE key = ?", (key,))
