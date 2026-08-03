from backend.interview_engine.models import CandidateProfile, InterviewConfiguration
from backend.interview_engine.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_interview_context,
    build_system_design_turn_instruction,
)


def test_system_prompt_is_versioned_and_bias_aware() -> None:
    assert PROMPT_VERSION in build_interview_context(
        InterviewConfiguration(job_listing="Backend engineer")
    )
    assert "Ask exactly one clear question at a time" in SYSTEM_PROMPT
    assert "protected or sensitive personal characteristics" in SYSTEM_PROMPT
    assert "Do not infer competence from identity" in SYSTEM_PROMPT


def test_context_preserves_candidate_and_user_inputs_as_delimited_data() -> None:
    configuration = InterviewConfiguration(
        candidate=CandidateProfile(name="Ada", skills=("Python", "Distributed systems")),
        job_listing="Build reliable APIs",
        company_info="Example Company",
        user_instructions="Include LangGraph",
    )

    context = build_interview_context(configuration)

    assert "Candidate name: Ada" in context
    assert "Python, Distributed systems" in context
    assert "<job-listing>" in context
    assert "Include LangGraph" in context


def test_system_design_handoff_requests_one_concise_next_move() -> None:
    instruction = build_system_design_turn_instruction()

    assert "single most useful next move" in instruction
    assert "one clarification" in instruction
    assert "trade-off" in instruction
    assert "do not provide coaching or evaluation" in instruction
