from yoyo import step

steps = [
    step(
        """
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            is_secret INTEGER NOT NULL DEFAULT 0 CHECK (is_secret IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS settings",
    ),
    step(
        """
        CREATE TABLE interview_attempts (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'ready',
            configuration_json TEXT NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS interview_attempts",
    ),
    step(
        """
        CREATE TABLE interview_messages (
            id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL REFERENCES interview_attempts(id) ON DELETE CASCADE,
            langgraph_message_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            role TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(attempt_id, langgraph_message_id),
            UNIQUE(attempt_id, sequence)
        )
        """,
        "DROP TABLE IF EXISTS interview_messages",
    ),
    step(
        "CREATE INDEX idx_interview_messages_attempt ON interview_messages(attempt_id, sequence)",
        "DROP INDEX IF EXISTS idx_interview_messages_attempt",
    ),
    step(
        """
        CREATE TABLE interview_graph_state (
            attempt_id TEXT NOT NULL REFERENCES interview_attempts(id) ON DELETE CASCADE,
            thread_id TEXT NOT NULL,
            checkpoint_namespace TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            checkpoint_version INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            state_json TEXT NOT NULL,
            channel_versions_json TEXT NOT NULL,
            versions_seen_json TEXT NOT NULL,
            updated_channels_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(thread_id, checkpoint_namespace)
        )
        """,
        "DROP TABLE IF EXISTS interview_graph_state",
    ),
    step(
        """
        CREATE TABLE interview_graph_writes (
            attempt_id TEXT NOT NULL REFERENCES interview_attempts(id) ON DELETE CASCADE,
            thread_id TEXT NOT NULL,
            checkpoint_namespace TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            task_path TEXT NOT NULL DEFAULT '',
            write_index INTEGER NOT NULL,
            channel TEXT NOT NULL,
            value_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(thread_id, checkpoint_namespace, checkpoint_id, task_id, write_index)
        )
        """,
        "DROP TABLE IF EXISTS interview_graph_writes",
    ),
    step(
        "CREATE INDEX idx_interview_graph_writes_checkpoint "
        "ON interview_graph_writes(thread_id, checkpoint_namespace, checkpoint_id)",
        "DROP INDEX IF EXISTS idx_interview_graph_writes_checkpoint",
    ),
]
