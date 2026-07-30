import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT OR IGNORE INTO settings (
            key, value, is_secret, created_at, updated_at
        ) VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            ("chat_model", "gpt-4o-mini"),
            ("theme", "system"),
        ),
    )
