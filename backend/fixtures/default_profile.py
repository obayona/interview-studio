import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO developer_profiles (id, created_at, updated_at)
        VALUES ('default', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
    )
