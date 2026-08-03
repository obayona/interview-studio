from yoyo import step

steps = [
    step(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            credentials_version INTEGER NOT NULL DEFAULT 1
                CHECK (credentials_version >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS users",
    ),
    step(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            csrf_token TEXT NOT NULL,
            credentials_version INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS sessions",
    ),
    step(
        "CREATE INDEX idx_sessions_user_expiry ON sessions(user_id, expires_at)",
        "DROP INDEX IF EXISTS idx_sessions_user_expiry",
    ),
]
