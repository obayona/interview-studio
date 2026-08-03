from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from backend.app.api.websocket import interview_websocket
from backend.app.repositories.auth import AuthenticatedSession


class AuthStub:
    enabled = True

    def __init__(self, authenticated: bool) -> None:
        self.authenticated = authenticated

    async def authenticate(self, token: str | None) -> AuthenticatedSession | None:
        if not self.authenticated or token is None:
            return None
        return AuthenticatedSession("default", "owner", "csrf", "later")


class WebSocketStub:
    def __init__(self, authenticated: bool, origin: str) -> None:
        self.app = SimpleNamespace(
            state=SimpleNamespace(
                auth=AuthStub(authenticated),
                config=SimpleNamespace(trusted_origins=("https://studio.example.com",)),
            )
        )
        self.cookies = {"interview_studio_session": "token"} if authenticated else {}
        self.headers = {"origin": origin}
        self.closed: tuple[int, str] | None = None

    async def close(self, code: int, reason: str) -> None:
        self.closed = (code, reason)


async def test_websocket_rejects_anonymous_and_untrusted_origins() -> None:
    anonymous = WebSocketStub(False, "https://studio.example.com")
    await interview_websocket(cast(Any, anonymous), "attempt")
    assert anonymous.closed == (4401, "Authentication required")

    untrusted = WebSocketStub(True, "https://attacker.example.com")
    await interview_websocket(cast(Any, untrusted), "attempt")
    assert untrusted.closed == (4403, "Origin is not allowed")
