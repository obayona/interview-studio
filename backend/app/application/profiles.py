from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from typing import Protocol

from PIL import Image, UnidentifiedImageError

from backend.app.core.config import SettingsService
from backend.app.core.errors import ApplicationError
from backend.app.domain.profile import (
    DeveloperProfile,
    ProfileSuggestions,
    ProfileUpdate,
)
from backend.app.repositories.profile import ProfileRepository
from backend.profile_parser import CVParser, PDFTextExtractor

MAX_AVATAR_SIZE = 2 * 1024 * 1024
MAX_AVATAR_DIMENSION = 4096
MAX_CV_SIZE = 10 * 1024 * 1024
AVATAR_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


class ProfileParser(Protocol):
    async def parse(self, text: str) -> ProfileSuggestions: ...


class TextExtractor(Protocol):
    def extract(self, content: bytes) -> str: ...


ParserFactory = Callable[[str, str], ProfileParser]


class ProfileService:
    def __init__(
        self,
        repository: ProfileRepository,
        settings: SettingsService,
        *,
        text_extractor: TextExtractor | None = None,
        parser: ProfileParser | None = None,
        parser_factory: ParserFactory = CVParser.from_openai,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._text_extractor = text_extractor or PDFTextExtractor()
        self._parser = parser
        self._parser_factory = parser_factory

    async def get(self) -> DeveloperProfile:
        return await self._repository.get()

    async def update(self, update: ProfileUpdate) -> DeveloperProfile:
        return await self._repository.update(update)

    async def set_avatar(self, content: bytes, mime_type: str) -> DeveloperProfile:
        if mime_type not in AVATAR_TYPES:
            raise self._validation_error("avatar", "Use a JPEG, PNG, or WebP image.")
        if not content or len(content) > MAX_AVATAR_SIZE:
            raise self._validation_error("avatar", "Avatar images must be 2 MB or smaller.")
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                image_format = image.format
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise self._validation_error("avatar", "The image is invalid.") from error
        if image_format != AVATAR_TYPES[mime_type]:
            raise self._validation_error(
                "avatar", "The uploaded content does not match its image type."
            )
        if width < 64 or height < 64 or max(width, height) > MAX_AVATAR_DIMENSION:
            raise self._validation_error(
                "avatar", "Avatar dimensions must be between 64 and 4096 pixels."
            )
        await self._repository.set_avatar(content, mime_type, width, height)
        return await self.get()

    async def get_avatar(self) -> tuple[bytes, str] | None:
        return await self._repository.get_avatar()

    async def delete_avatar(self) -> DeveloperProfile:
        await self._repository.delete_avatar()
        return await self.get()

    async def import_cv(self, content: bytes, filename: str, mime_type: str) -> ProfileSuggestions:
        if mime_type != "application/pdf" or not filename.casefold().endswith(".pdf"):
            raise self._validation_error("cv", "Only PDF CV files are supported.")
        if not content or len(content) > MAX_CV_SIZE:
            raise self._validation_error("cv", "CV files must be 10 MB or smaller.")
        if not content.startswith(b"%PDF"):
            raise self._validation_error("cv", "The uploaded file is not a valid PDF.")
        try:
            extracted_text = self._text_extractor.extract(content)
        except (ValueError, OSError) as error:
            raise self._validation_error("cv", str(error)) from error
        parser = self._parser
        if parser is None:
            ai = await self._settings.ai()
            if not ai.interview_ready:
                raise ApplicationError(
                    code="provider_not_configured",
                    message="Configure an OpenAI API key before importing a CV.",
                    status_code=503,
                )
            parser = self._parser_factory(ai.api_key, ai.chat_model)
        try:
            return await parser.parse(extracted_text)
        except Exception as error:
            raise ApplicationError(
                code="cv_ai_extraction_failed",
                message="The CV could not be interpreted by the AI provider.",
                status_code=502,
            ) from error

    def _validation_error(self, field: str, message: str) -> ApplicationError:
        return ApplicationError(
            code="profile_validation_error",
            message="Profile input is invalid.",
            status_code=422,
            field_errors={field: [message]},
        )
