from __future__ import annotations

import json
from collections.abc import Mapping
from enum import Enum
from typing import Any

from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict


class UnsupportedCheckpointValueError(TypeError):
    pass


class StrictJsonCodec:
    """Versioned JSON codec with no binary or implicit object fallback."""

    VERSION = 1

    def dumps(self, value: Any) -> str:
        adapted = self._adapt(value, path="$")
        return json.dumps(
            {"codec_version": self.VERSION, "value": adapted},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def loads(self, payload: str) -> Any:
        envelope = json.loads(payload)
        if not isinstance(envelope, dict) or envelope.get("codec_version") != self.VERSION:
            raise ValueError("Unsupported checkpoint JSON codec version")
        return envelope["value"]

    def dumps_message(self, message: BaseMessage) -> str:
        if not message.id:
            raise ValueError("Completed transcript messages require a stable message ID")
        return self.dumps(message_to_dict(message))

    def loads_message(self, payload: str) -> BaseMessage:
        value = self.loads(payload)
        if not isinstance(value, dict):
            raise ValueError("Stored message must be a JSON object")
        return messages_from_dict([value])[0]

    def _adapt(self, value: Any, *, path: str) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Enum):
            return self._adapt(value.value, path=path)
        if isinstance(value, BaseMessage):
            return self._adapt(message_to_dict(value), path=path)
        if isinstance(value, (bytes, bytearray, memoryview)):
            raise UnsupportedCheckpointValueError(f"{path}: binary values are not supported")
        if isinstance(value, (list, tuple)):
            return [self._adapt(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise UnsupportedCheckpointValueError(f"{path}: object keys must be strings")
                result[key] = self._adapt(item, path=f"{path}.{key}")
            return result
        raise UnsupportedCheckpointValueError(
            f"{path}: unsupported checkpoint value type {type(value).__name__}"
        )
