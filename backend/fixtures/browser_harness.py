import sqlite3

CONFIGURATION_JSON = (
    '{"candidate":{"name":"Candidate","headline":"","summary":"","skills":[],'
    '"years_experience":null,"portfolio_url":null,"linkedin_url":null},'
    '"job_listing":"Practice a general software engineering interview.",'
    '"company_info":"","interview_type":"mixed","interviewer_profile":"tech_lead",'
    '"difficulty":"mid","user_instructions":"","language":"English","topics":[],'
    '"limits":{"max_questions":8,"max_duration_minutes":30,'
    '"follow_up_questions_per_topic":1}}'
)


def apply(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO interview_attempts (
            id, thread_id, status, configuration_json, created_at, updated_at
        ) VALUES (
            'browser-harness', 'browser-harness-default', 'ready', ?,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        """,
        (CONFIGURATION_JSON,),
    )
