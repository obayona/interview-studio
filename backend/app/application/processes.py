from __future__ import annotations

import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from backend.app.core.config import SettingsService
from backend.app.core.errors import ApplicationError
from backend.app.domain.processes import (
    ContentSource,
    ImportPreview,
    InterviewProcess,
    ProcessCreate,
    ProcessSummary,
    ProcessUpdate,
)
from backend.app.repositories.processes import ProcessRepository
from backend.app.repositories.profile import ProfileRepository
from backend.interview_engine.models import CandidateProfile, InterviewConfiguration

MAX_IMPORTED_BYTES = 1_000_000
MAX_IMPORTED_CHARS = 50_000
MAX_REDIRECTS = 3


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored and data.strip():
            self.parts.append(data.strip())


class SafeContentFetcher:
    async def fetch(self, url: str) -> ImportPreview:
        current = url
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
            for _ in range(MAX_REDIRECTS + 1):
                await self._validate_public_url(current)
                async with client.stream(
                    "GET",
                    current,
                    headers={"User-Agent": "InterviewStudio/1.0"},
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            break
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise self._error("The URL could not be fetched.")
                    content_type = response.headers.get("content-type", "")
                    if not (
                        content_type.startswith("text/html")
                        or content_type.startswith("text/plain")
                    ):
                        raise self._error("The URL must return HTML or plain text.")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_IMPORTED_BYTES:
                            raise self._error("The imported page is too large.")
                text = bytes(content).decode(response.encoding or "utf-8", errors="replace")
                return ImportPreview(
                    url=current,
                    content=self._normalize(text, "text/html" in content_type),
                )
        raise self._error("The URL redirected too many times.")

    async def _validate_public_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise self._error("Only public HTTP and HTTPS URLs are supported.")
        if parsed.port not in {None, 80, 443}:
            raise self._error("Only standard HTTP and HTTPS ports are supported.")
        try:
            direct_ip = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            direct_ip = None
        if direct_ip is not None:
            if not direct_ip.is_global:
                raise self._error("Private and local network URLs are not allowed.")
            return
        try:
            addresses = await __import__("asyncio").to_thread(
                socket.getaddrinfo, parsed.hostname, parsed.port or 443
            )
        except socket.gaierror as error:
            raise self._error("The URL hostname could not be resolved.") from error
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise self._error("Private and local network URLs are not allowed.")

    @staticmethod
    def _normalize(content: str, html: bool) -> str:
        if html:
            parser = _TextExtractor()
            parser.feed(content)
            content = "\n".join(parser.parts)
        normalized = "\n".join(line.strip() for line in content.splitlines() if line.strip())
        if not normalized:
            raise SafeContentFetcher._error("The URL did not contain readable text.")
        return normalized[:MAX_IMPORTED_CHARS]

    @staticmethod
    def _error(message: str) -> ApplicationError:
        return ApplicationError("process_import_failed", message, 422)


class ProcessService:
    def __init__(
        self,
        repository: ProcessRepository,
        profiles: ProfileRepository,
        settings: SettingsService,
        fetcher: SafeContentFetcher | None = None,
    ) -> None:
        self._repository = repository
        self._profiles = profiles
        self._settings = settings
        self._fetcher = fetcher or SafeContentFetcher()

    async def list(self) -> list[ProcessSummary]:
        return await self._repository.list_all()

    async def get(self, process_id: str) -> InterviewProcess:
        process = await self._repository.get(process_id)
        if process is None:
            raise self._not_found(process_id)
        return process

    async def preview(self, url: str) -> ImportPreview:
        return await self._fetcher.fetch(url)

    async def create(self, payload: ProcessCreate) -> InterviewProcess:
        job_text, job_url = await self._resolve(payload.job)
        company_text, company_url = await self._resolve(payload.company)
        return await self._repository.create(
            title=payload.title.strip(),
            company_name=payload.company_name.strip(),
            target_role=payload.target_role.strip(),
            job_description=job_text,
            company_info=company_text,
            job_source_url=job_url,
            company_source_url=company_url,
            stages=payload.stages,
        )

    async def update(self, process_id: str, payload: ProcessUpdate) -> InterviewProcess:
        values = payload.model_dump(exclude_unset=True, exclude={"job", "company", "stages"})
        if payload.job is not None:
            values["job_description"], values["job_source_url"] = await self._resolve(payload.job)
        if payload.company is not None:
            values["company_info"], values["company_source_url"] = await self._resolve(
                payload.company
            )
        try:
            process = await self._repository.update(process_id, values, payload.stages)
        except ValueError as error:
            raise ApplicationError("process_stage_history_conflict", str(error), 409) from error
        if process is None:
            raise self._not_found(process_id)
        return process

    async def delete(self, process_id: str) -> None:
        if not await self._repository.delete(process_id):
            raise self._not_found(process_id)

    async def start_attempt(self, process_id: str, stage_id: str) -> dict[str, object]:
        process = await self.get(process_id)
        stage = next((item for item in process.stages if item.id == stage_id), None)
        if stage is None:
            raise ApplicationError("stage_not_found", "Interview stage was not found.", 404)
        if not stage.enabled:
            raise ApplicationError("stage_disabled", "Enable this stage before starting it.", 409)
        profile = await self._profiles.get()
        links = {link.link_type: str(link.url) for link in profile.links}
        candidate = CandidateProfile.model_validate(
            {
                "name": profile.full_name or "Candidate",
                "headline": profile.headline,
                "summary": profile.summary,
                "skills": tuple(profile.skills),
                "portfolio_url": links.get("portfolio"),
                "linkedin_url": links.get("linkedin"),
            }
        )
        configuration = InterviewConfiguration(
            candidate=candidate,
            job_listing=process.job_description,
            company_info=process.company_info,
            interview_type=stage.stage_type,
            **stage.configuration.model_dump(),
        )
        ai = await self._settings.ai()
        created = await self._repository.create_attempt(
            process_id,
            stage_id,
            configuration.model_dump_json(),
            text_to_speech=ai.tts_enabled,
        )
        if created is None:
            raise ApplicationError("stage_not_startable", "This stage cannot be started.", 409)
        attempt_id, attempt_number = created
        return {"id": attempt_id, "attempt_number": attempt_number, "status": "ready"}

    async def _resolve(self, source: ContentSource | None) -> tuple[str, str | None]:
        if source is None:
            return "", None
        if source.kind == "text":
            return source.value.strip(), None
        preview = await self.preview(source.value)
        return preview.content, preview.url

    @staticmethod
    def _not_found(process_id: str) -> ApplicationError:
        return ApplicationError(
            "process_not_found",
            f"Interview process '{process_id}' was not found.",
            404,
        )
