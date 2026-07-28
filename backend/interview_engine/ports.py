from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
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
    def transcribe(self, chunks: AsyncIterator[AudioChunk]) -> AsyncIterator[TranscriptChunk]:
        raise NotImplementedError


class TextToSpeechPort(ABC):
    @abstractmethod
    def synthesize(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]:
        raise NotImplementedError
