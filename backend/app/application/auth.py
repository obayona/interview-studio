from __future__ import annotations

import asyncio
import hmac
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from backend.app.repositories.auth import AuthenticatedSession, AuthRepository


class AuthenticationFailedError(Exception):
    pass


class LoginRateLimitedError(Exception):
    pass


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        *,
        enabled: bool,
        username: str,
        password: str,
        session_lifetime_seconds: int,
    ) -> None:
        self.enabled = enabled
        self._repository = repository
        self._username = username
        self._password = password
        self._session_lifetime_seconds = session_lifetime_seconds
        self._hasher = PasswordHasher()
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._attempt_lock = asyncio.Lock()

    async def initialize(self) -> None:
        if not self.enabled:
            return
        current = await self._repository.user_credentials()
        changed = current is None or current[0] != self._username
        if current is not None and not changed:
            try:
                changed = not self._hasher.verify(current[1], self._password)
            except (InvalidHashError, VerifyMismatchError):
                changed = True
        if changed:
            password_hash = self._hasher.hash(self._password)
        else:
            assert current is not None
            password_hash = current[1]
        await self._repository.reconcile_user(self._username, password_hash, changed)

    async def login(
        self, username: str, password: str, client_key: str
    ) -> tuple[str, AuthenticatedSession]:
        await self._check_rate_limit(client_key)
        credentials = await self._repository.user_credentials()
        valid = False
        if credentials is not None and hmac.compare_digest(credentials[0], username):
            try:
                valid = self._hasher.verify(credentials[1], password)
            except (InvalidHashError, VerifyMismatchError):
                valid = False
        if not valid:
            await self._record_failure(client_key)
            raise AuthenticationFailedError
        await self._clear_failures(client_key)
        return await self._repository.create_session(self._session_lifetime_seconds)

    async def authenticate(self, raw_token: str | None) -> AuthenticatedSession | None:
        if not self.enabled:
            return AuthenticatedSession("development", "development", "", "")
        if not raw_token:
            return None
        return await self._repository.session(raw_token)

    async def logout(self, raw_token: str | None) -> None:
        if raw_token:
            await self._repository.delete_session(raw_token)

    async def _check_rate_limit(self, key: str) -> None:
        now = time.monotonic()
        async with self._attempt_lock:
            attempts = self._attempts[key]
            while attempts and now - attempts[0] > 300:
                attempts.popleft()
            if len(attempts) >= 5:
                raise LoginRateLimitedError

    async def _record_failure(self, key: str) -> None:
        async with self._attempt_lock:
            self._attempts[key].append(time.monotonic())

    async def _clear_failures(self, key: str) -> None:
        async with self._attempt_lock:
            self._attempts.pop(key, None)
