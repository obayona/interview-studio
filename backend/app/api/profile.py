from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import Response

from backend.app.application.profiles import (
    MAX_AVATAR_SIZE,
    MAX_CV_SIZE,
    ProfileService,
)
from backend.app.core.errors import ApplicationError
from backend.app.domain.profile import (
    DeveloperProfile,
    ProfileSuggestions,
    ProfileUpdate,
)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


def service(request: Request) -> ProfileService:
    return cast(ProfileService, request.app.state.profile)


async def read_limited(upload: UploadFile, limit: int) -> bytes:
    content = await upload.read(limit + 1)
    await upload.close()
    if len(content) > limit:
        raise ApplicationError(
            code="profile_file_too_large",
            message="The uploaded file exceeds the allowed size.",
            status_code=413,
        )
    return content


@router.get("")
async def get_profile(request: Request) -> DeveloperProfile:
    return await service(request).get()


@router.patch("")
async def update_profile(request: Request, update: ProfileUpdate) -> DeveloperProfile:
    return await service(request).update(update)


@router.post("/avatar")
async def upload_avatar(request: Request, file: Annotated[UploadFile, File()]) -> DeveloperProfile:
    content = await read_limited(file, MAX_AVATAR_SIZE)
    return await service(request).set_avatar(
        content, file.content_type or "application/octet-stream"
    )


@router.get("/avatar")
async def get_avatar(request: Request) -> Response:
    avatar = await service(request).get_avatar()
    if avatar is None:
        raise ApplicationError(
            code="profile_avatar_not_found",
            message="The profile does not have an avatar.",
            status_code=404,
        )
    content, mime_type = avatar
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/avatar")
async def delete_avatar(request: Request) -> DeveloperProfile:
    return await service(request).delete_avatar()


@router.post("/cv/import")
async def import_cv(request: Request, file: Annotated[UploadFile, File()]) -> ProfileSuggestions:
    content = await read_limited(file, MAX_CV_SIZE)
    return await service(request).import_cv(
        content,
        file.filename or "resume.pdf",
        file.content_type or "application/octet-stream",
    )
