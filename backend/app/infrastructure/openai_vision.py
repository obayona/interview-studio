from __future__ import annotations

import base64

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from backend.interview_engine.ports import DiagramObserverPort


class OpenAIDiagramObserver(DiagramObserverPort):
    """Convert a submitted whiteboard image into concise interview context."""

    def __init__(self, api_key: str, model: str) -> None:
        self._model = ChatOpenAI(api_key=SecretStr(api_key), model=model, temperature=0)

    async def observe(self, png: bytes, context: str) -> str:
        encoded = base64.b64encode(png).decode("ascii")
        response = await self._model.ainvoke(
            [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                "Inspect this software-system architecture whiteboard. "
                                "Describe only visible components, connections, annotations, "
                                "boundaries, and notable missing or ambiguous areas in at most "
                                "180 words. Do not grade it and do not invent unreadable "
                                "labels.\n\n"
                                f"Interview context:\n{context}"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{encoded}"},
                        },
                    ]
                )
            ]
        )
        return response.text.strip()
