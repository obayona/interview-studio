from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioChunk:
    data: bytes
    media_type: str
    sequence: int


@dataclass(frozen=True, slots=True)
class TranscriptChunk:
    text: str
    is_final: bool
    sequence: int


class SpeechToTextPort(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, filename: str) -> str:
        raise NotImplementedError


class TextToSpeechPort(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError


class DiagramObserverPort(ABC):
    @abstractmethod
    async def observe(self, png: bytes, context: str) -> str:
        raise NotImplementedError
