from yoyo import step

steps = [
    step(
        """
        CREATE TABLE interview_reports (
            id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL
                REFERENCES interview_attempts(id) ON DELETE CASCADE,
            evaluation_version INTEGER NOT NULL CHECK (evaluation_version >= 1),
            schema_version TEXT NOT NULL,
            overall_score INTEGER NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
            report_json TEXT NOT NULL,
            model_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(attempt_id, evaluation_version)
        )
        """,
        "DROP TABLE IF EXISTS interview_reports",
    ),
    step(
        "CREATE INDEX idx_reports_attempt ON interview_reports(attempt_id)",
        "DROP INDEX IF EXISTS idx_reports_attempt",
    ),
]
