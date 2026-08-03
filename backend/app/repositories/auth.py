from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.app.core.database import SQLiteManager


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    return value.isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthenticatedSession:
    user_id: str
    username: str
    csrf_token: str
    expires_at: str


class AuthRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def reconcile_user(self, username: str, password_hash: str, changed: bool) -> None:
        timestamp = _timestamp(_now())
        async with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT id, username, credentials_version FROM users LIMIT 1"
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO users (
                        id, username, password_hash, credentials_version, created_at, updated_at
                    ) VALUES ('default', ?, ?, 1, ?, ?)
                    """,
                    (username, password_hash, timestamp, timestamp),
                )
                return
            if changed or str(row["username"]) != username:
                version = int(row["credentials_version"]) + 1
                connection.execute(
                    """
                    UPDATE users
                    SET username = ?, password_hash = ?, credentials_version = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (username, password_hash, version, timestamp, row["id"]),
                )
                connection.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))

    async def user_credentials(self) -> tuple[str, str] | None:
        row = await self._database.fetchone("SELECT username, password_hash FROM users LIMIT 1")
        if row is None:
            return None
        return str(row["username"]), str(row["password_hash"])

    async def create_session(self, lifetime_seconds: int) -> tuple[str, AuthenticatedSession]:
        raw_token = secrets.token_urlsafe(48)
        csrf_token = secrets.token_urlsafe(32)
        now = _now()
        expires = now + timedelta(seconds=lifetime_seconds)
        session_id = secrets.token_hex(16)
        async with self._database.transaction() as connection:
            user = connection.execute(
                "SELECT id, username, credentials_version FROM users LIMIT 1"
            ).fetchone()
            if user is None:
                raise RuntimeError("Server user has not been initialized")
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (_timestamp(now),))
            connection.execute(
                """
                INSERT INTO sessions (
                    id, user_id, token_hash, csrf_token, credentials_version,
                    expires_at, created_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user["id"],
                    token_hash(raw_token),
                    csrf_token,
                    user["credentials_version"],
                    _timestamp(expires),
                    _timestamp(now),
                    _timestamp(now),
                ),
            )
        return raw_token, AuthenticatedSession(
            user_id=str(user["id"]),
            username=str(user["username"]),
            csrf_token=csrf_token,
            expires_at=_timestamp(expires),
        )

    async def session(self, raw_token: str) -> AuthenticatedSession | None:
        now = _timestamp(_now())
        row = await self._database.fetchone(
            """
            SELECT s.id, s.csrf_token, s.expires_at, s.credentials_version,
                   u.id AS user_id, u.username, u.credentials_version AS user_version
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (token_hash(raw_token), now),
        )
        if row is None or int(row["credentials_version"]) != int(row["user_version"]):
            return None
        async with self._database.transaction() as connection:
            connection.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE id = ?", (now, row["id"])
            )
        return AuthenticatedSession(
            user_id=str(row["user_id"]),
            username=str(row["username"]),
            csrf_token=str(row["csrf_token"]),
            expires_at=str(row["expires_at"]),
        )

    async def delete_session(self, raw_token: str) -> None:
        async with self._database.transaction() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (token_hash(raw_token),)
            )
