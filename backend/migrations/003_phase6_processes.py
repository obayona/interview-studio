from yoyo import step

steps = [
    step(
        """
        CREATE TABLE interview_processes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company_name TEXT NOT NULL DEFAULT '',
            target_role TEXT NOT NULL,
            job_description TEXT NOT NULL,
            company_info TEXT NOT NULL DEFAULT '',
            job_source_url TEXT,
            company_source_url TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'completed', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS interview_processes",
    ),
    step(
        """
        CREATE TABLE interview_stages (
            id TEXT PRIMARY KEY,
            process_id TEXT NOT NULL
                REFERENCES interview_processes(id) ON DELETE CASCADE,
            stage_type TEXT NOT NULL,
            position INTEGER NOT NULL CHECK (position >= 0),
            enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
            status TEXT NOT NULL DEFAULT 'not_started'
                CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped')),
            configuration_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(process_id, position)
        )
        """,
        "DROP TABLE IF EXISTS interview_stages",
    ),
    step(
        """
        CREATE TABLE interview_attempts (
            id TEXT PRIMARY KEY,
            stage_id TEXT REFERENCES interview_stages(id) ON DELETE CASCADE,
            attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
            thread_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'ready',
            configuration_json TEXT NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            termination_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS interview_attempts",
    ),
    step(
        "CREATE UNIQUE INDEX idx_attempt_stage_number "
        "ON interview_attempts(stage_id, attempt_number) WHERE stage_id IS NOT NULL",
        "DROP INDEX IF EXISTS idx_attempt_stage_number",
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
        CREATE TABLE audio_artifacts (
            id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL REFERENCES interview_attempts(id) ON DELETE CASCADE,
            message_id TEXT REFERENCES interview_messages(id) ON DELETE SET NULL,
            direction TEXT NOT NULL CHECK (direction IN ('input', 'output')),
            media_type TEXT NOT NULL,
            duration_ms INTEGER,
            data BLOB,
            created_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS audio_artifacts",
    ),
    step(
        "CREATE INDEX idx_audio_artifacts_attempt ON audio_artifacts(attempt_id, created_at)",
        "DROP INDEX IF EXISTS idx_audio_artifacts_attempt",
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
            PRIMARY KEY(
                thread_id, checkpoint_namespace, checkpoint_id, task_id, write_index
            )
        )
        """,
        "DROP TABLE IF EXISTS interview_graph_writes",
    ),
    step(
        "CREATE INDEX idx_interview_graph_writes_checkpoint "
        "ON interview_graph_writes(thread_id, checkpoint_namespace, checkpoint_id)",
        "DROP INDEX IF EXISTS idx_interview_graph_writes_checkpoint",
    ),
    step(
        "CREATE INDEX idx_stages_process ON interview_stages(process_id, position)",
        "DROP INDEX IF EXISTS idx_stages_process",
    ),
]
