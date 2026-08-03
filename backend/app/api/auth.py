from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response
from pydantic import BaseModel, Field

from backend.app.application.auth import (
    AuthenticationFailedError,
    AuthService,
    LoginRateLimitedError,
)
from backend.app.core.errors import ApplicationError

SESSION_COOKIE = "interview_studio_session"
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


def _session_payload(username: str, csrf_token: str, expires_at: str) -> dict[str, object]:
    return {
        "authenticated": True,
        "username": username,
        "csrf_token": csrf_token,
        "expires_at": expires_at,
    }


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, object]:
    service: AuthService = request.app.state.auth
    if not service.enabled:
        return _session_payload("development", "", "")
    client_key = request.client.host if request.client else "unknown"
    try:
        token, session = await service.login(payload.username, payload.password, client_key)
    except LoginRateLimitedError as error:
        raise ApplicationError(
            code="login_rate_limited",
            message="Too many login attempts. Try again later.",
            status_code=429,
        ) from error
    except AuthenticationFailedError as error:
        raise ApplicationError(
            code="authentication_failed",
            message="The username or password is incorrect.",
            status_code=401,
        ) from error
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=request.app.state.config.session_lifetime_seconds,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return _session_payload(session.username, session.csrf_token, session.expires_at)


@router.get("/session")
async def session(request: Request) -> dict[str, object]:
    service: AuthService = request.app.state.auth
    current = getattr(request.state, "auth_session", None) or await service.authenticate(None)
    if current is None:
        raise ApplicationError(
            code="authentication_required",
            message="Sign in to continue.",
            status_code=401,
        )
    return _session_payload(current.username, current.csrf_token, current.expires_at)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    service: AuthService = request.app.state.auth
    await service.logout(session_token)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
