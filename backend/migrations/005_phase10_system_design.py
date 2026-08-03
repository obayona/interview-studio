from yoyo import step

steps = [
    step(
        """
        CREATE TABLE system_design_sessions (
            attempt_id TEXT PRIMARY KEY
                REFERENCES interview_attempts(id) ON DELETE CASCADE,
            scene_json TEXT NOT NULL,
            scene_version INTEGER NOT NULL CHECK (scene_version >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS system_design_sessions",
    ),
    step(
        """
        CREATE TABLE system_design_snapshots (
            id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL
                REFERENCES system_design_sessions(attempt_id) ON DELETE CASCADE,
            scene_version INTEGER NOT NULL CHECK (scene_version >= 1),
            png_blob BLOB NOT NULL,
            reason TEXT NOT NULL
                CHECK (reason IN ('periodic', 'explicit', 'interview_end')),
            transcript_message_id TEXT
                REFERENCES interview_messages(id) ON DELETE SET NULL,
            observation_text TEXT,
            observed_at TEXT,
            created_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS system_design_snapshots",
    ),
    step(
        "CREATE INDEX idx_system_design_snapshots_attempt "
        "ON system_design_snapshots(attempt_id, created_at)",
        "DROP INDEX IF EXISTS idx_system_design_snapshots_attempt",
    ),
]
