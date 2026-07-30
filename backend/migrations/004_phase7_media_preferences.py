from yoyo import step

steps = [
    step(
        "ALTER TABLE interview_attempts ADD COLUMN current_stt_enabled INTEGER "
        "CHECK (current_stt_enabled IN (0, 1))",
        """
        ALTER TABLE interview_attempts DROP COLUMN current_stt_enabled
        """,
    ),
    step(
        "ALTER TABLE interview_attempts ADD COLUMN current_tts_enabled INTEGER "
        "CHECK (current_tts_enabled IN (0, 1))",
        """
        ALTER TABLE interview_attempts DROP COLUMN current_tts_enabled
        """,
    ),
]
