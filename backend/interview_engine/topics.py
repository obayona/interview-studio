from backend.interview_engine.models import InterviewType

DEFAULT_TOPICS: dict[InterviewType, tuple[str, ...]] = {
    InterviewType.SCREENING: (
        "career motivation and role alignment",
        "relevant experience",
        "availability and expectations",
    ),
    InterviewType.BEHAVIORAL: (
        "collaboration",
        "ownership and accountability",
        "conflict resolution",
        "learning from failure",
        "communication",
    ),
    InterviewType.TECHNICAL: (
        "technical fundamentals for the role",
        "implementation trade-offs",
        "testing and reliability",
        "debugging and problem-solving",
    ),
    InterviewType.EXPERIENCE: (
        "recent project impact",
        "technical decisions",
        "individual contribution",
        "lessons and growth",
    ),
    InterviewType.SYSTEM_DESIGN: (
        "requirements and constraints",
        "high-level architecture",
        "data model and interfaces",
        "scalability and reliability",
        "trade-offs and evolution",
    ),
    InterviewType.MIXED: (
        "role motivation",
        "relevant project experience",
        "technical fundamentals",
        "problem-solving",
        "collaboration and communication",
    ),
}


def topics_for(interview_type: InterviewType) -> tuple[str, ...]:
    return DEFAULT_TOPICS[interview_type]
