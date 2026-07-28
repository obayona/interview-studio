from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.interview_engine import InterviewType
from backend.interview_engine.graph import determine_termination, elapsed_seconds
from backend.interview_engine.models import (
    CandidateProfile,
    InterviewConfiguration,
    InterviewLimits,
    TerminationReason,
)
from backend.interview_engine.state import InterviewState
from backend.interview_engine.topics import topics_for


def configuration(**values: object) -> InterviewConfiguration:
    return InterviewConfiguration(job_listing="Backend engineer", **values)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (InterviewState(user_requested_end=True), TerminationReason.USER_REQUESTED),
        (
            InterviewState(elapsed_seconds=1_801, question_count=0),
            TerminationReason.TIME_LIMIT,
        ),
        (
            InterviewState(elapsed_seconds=0, question_count=8),
            TerminationReason.QUESTION_LIMIT,
        ),
        (
            InterviewState(
                elapsed_seconds=0,
                question_count=1,
                topics=["testing"],
                topics_covered=["testing"],
            ),
            TerminationReason.TOPICS_COVERED,
        ),
        (
            InterviewState(
                elapsed_seconds=0,
                question_count=1,
                topics=["testing"],
                topics_covered=[],
            ),
            None,
        ),
    ],
)
def test_termination_rules(
    state: InterviewState,
    expected: TerminationReason | None,
) -> None:
    assert determine_termination(state, configuration()) == expected


def test_elapsed_time_is_non_negative() -> None:
    now = datetime.now(UTC)

    assert elapsed_seconds((now - timedelta(seconds=15)).isoformat(), now) == 15
    assert elapsed_seconds((now + timedelta(seconds=15)).isoformat(), now) == 0


def test_candidate_skills_are_normalized() -> None:
    candidate = CandidateProfile(skills=("Python", " Python ", "", "SQLite"))

    assert candidate.skills == ("Python", "SQLite")


def test_invalid_limits_are_rejected() -> None:
    with pytest.raises(ValidationError):
        InterviewLimits(max_questions=0)


def test_every_interview_type_has_a_topic_plan() -> None:
    assert all(topics_for(interview_type) for interview_type in InterviewType)
