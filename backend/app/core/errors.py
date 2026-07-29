from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int
    field_errors: dict[str, list[str]] = field(default_factory=dict)


class ProviderNotConfiguredError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="provider_not_configured",
            message="Configure an OpenAI API key before starting an interview.",
            status_code=503,
        )


class AttemptNotFoundError(ApplicationError):
    def __init__(self, attempt_id: str) -> None:
        super().__init__(
            code="attempt_not_found",
            message=f"Interview attempt '{attempt_id}' was not found.",
            status_code=404,
        )
