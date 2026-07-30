from __future__ import annotations

from io import BytesIO

from openai import AsyncOpenAI

from backend.interview_engine.ports import SpeechToTextPort, TextToSpeechPort


class OpenAISpeechToText(SpeechToTextPort):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=45.0, max_retries=1)
        self._model = model

    async def transcribe(self, audio: bytes, filename: str) -> str:
        result = await self._client.audio.transcriptions.create(
            model=self._model,
            file=(filename, BytesIO(audio)),
            response_format="text",
        )
        return str(result).strip()


class OpenAITextToSpeech(TextToSpeechPort):
    def __init__(self, api_key: str, model: str, voice: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=45.0, max_retries=1)
        self._model = model
        self._voice = voice

    async def synthesize(self, text: str) -> bytes:
        response = await self._client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="mp3",
        )
        return await response.aread()
