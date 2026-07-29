from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

from yoyo import get_backend, read_migrations


class SQLiteManager:
    """Own the application's single SQLite connection and transaction lock."""

    def __init__(self, database_path: Path, migrations_path: Path) -> None:
        self.database_path = database_path
        self.migrations_path = migrations_path
        self._connection: sqlite3.Connection | None = None
        self._transaction_lock = asyncio.Lock()

    async def start(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        # Yoyo's SQLite backend is synchronous; startup is intentionally gated
        # until migrations complete before accepting requests.
        self._migrate()
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.commit()
        self._connection = connection

    async def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("SQLite manager has not been started")
        return self._connection

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[sqlite3.Connection]:
        async with self._transaction_lock:
            connection = self.connection
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    async def fetchone(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        async with self._transaction_lock:
            cursor = self.connection.execute(sql, parameters)
            return cast(sqlite3.Row | None, cursor.fetchone())

    async def fetchall(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        async with self._transaction_lock:
            cursor = self.connection.execute(sql, parameters)
            return list(cursor.fetchall())

    def _migrate(self) -> None:
        backend = get_backend(f"sqlite:///{self.database_path}")
        migrations = read_migrations(str(self.migrations_path))
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))
