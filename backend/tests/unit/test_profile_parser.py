from typing import cast
from unittest.mock import Mock

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableLambda

from backend.profile_parser import CVParser


async def test_cv_parser_uses_structured_ai_result() -> None:
    structured_result = {
        "full_name": "Oswaldo A. Bayona",
        "headline": "Full-Stack & AI Engineer | SaaS Builder",
        "summary": "Full-Stack engineer with 7+ years of experience building SaaS platforms.",
        "location": None,
        "email": "bayonandrade@gmail.com",
        "phone": None,
        "skills": ["SaaS architecture", "React", "Laravel", "Django"],
        "experiences": [
            {
                "employer": "Fahrenheit Marketing",
                "role": "Senior Developer",
                "start_date": "2023-01-01",
                "end_date": "2026-01-01",
                "is_current": True,
                "description": "Led development of TrackNotion.",
            }
        ],
        "projects": [],
    }

    async def structured_response(_messages: object) -> dict[str, object]:
        return structured_result

    model = Mock()
    model.with_structured_output.return_value = RunnableLambda(structured_response)

    suggestions = await CVParser(cast(BaseChatModel, model)).parse(
        "Resume text with an unconventional visual layout"
    )

    model.with_structured_output.assert_called_once()
    assert suggestions.full_name == "Oswaldo A. Bayona"
    assert suggestions.headline == "Full-Stack & AI Engineer | SaaS Builder"
    assert suggestions.email == "bayonandrade@gmail.com"
    assert suggestions.experiences[0].employer == "Fahrenheit Marketing"
    assert suggestions.experiences[0].role == "Senior Developer"
    assert suggestions.experiences[0].is_current is False
    assert suggestions.experiences[0].position == 0
