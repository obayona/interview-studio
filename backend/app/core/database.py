from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast


class SQLiteManager:
    """Own the application's single SQLite connection and transaction lock."""

    def __init__(self, database_path: Path, migrations_path: Path) -> None:
        self.database_path = database_path
        self.migrations_path = migrations_path
        self._connection: sqlite3.Connection | None = None
        self._transaction_lock = asyncio.Lock()

    async def start(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        # Connect with autocommit=True to run PRAGMAs outside a transaction
        connection = sqlite3.connect(self.database_path, autocommit=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        # Switch to autocommit=False for implicit transaction management
        connection.autocommit = False
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
    async def transaction(
        self,
    ) -> AsyncGenerator[sqlite3.Connection, None]:
        async with self._transaction_lock:
            connection = self.connection
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
            result = cursor.fetchone()
            self.connection.commit()
            return cast(sqlite3.Row | None, result)

    async def fetchall(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        async with self._transaction_lock:
            cursor = self.connection.execute(sql, parameters)
            result = list(cursor.fetchall())
            self.connection.commit()
            return result
