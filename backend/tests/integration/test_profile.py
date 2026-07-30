from __future__ import annotations

from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from backend.app.application.profiles import ProfileService
from backend.app.core.config import AppConfig
from backend.app.domain.profile import ProfileSuggestions, WorkExperience
from backend.app.main import create_app
from backend.app.repositories.profile import ProfileRepository
from backend.tests.integration.helpers import prepare_database


class FakeCVParser:
    async def parse(self, text: str) -> ProfileSuggestions:
        assert "Taylor Example" in text
        return ProfileSuggestions(
            full_name="Taylor Example",
            headline="Staff Engineer",
            summary="Imported summary",
            email="taylor@example.com",
            skills=["Python", "SQLite"],
            experiences=[
                WorkExperience(
                    employer="Example Inc",
                    role="Engineer",
                    is_current=True,
                    position=0,
                )
            ],
        )


class FakeTextExtractor:
    def extract(self, content: bytes) -> str:
        assert content.startswith(b"%PDF")
        return "Taylor Example\nStaff Engineer"


def avatar_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (128, 128), "#2563eb").save(output, format="PNG")
    return output.getvalue()


async def test_profile_aggregate_avatar_and_transient_cv_import(tmp_path: Path) -> None:
    config = AppConfig(
        database_path=tmp_path / "profile.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        app.state.profile = ProfileService(
            ProfileRepository(app.state.database),
            app.state.settings,
            text_extractor=FakeTextExtractor(),
            parser=FakeCVParser(),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            initial = await client.get("/api/v1/profile")
            assert initial.status_code == 200
            assert initial.json()["full_name"] == ""

            updated = await client.patch(
                "/api/v1/profile",
                json={
                    "full_name": "Manual Name",
                    "headline": "Backend Engineer",
                    "summary": "Keep this manual summary",
                    "skills": ["Python", "FastAPI"],
                    "links": [
                        {
                            "link_type": "linkedin",
                            "url": "https://linkedin.com/in/manual",
                            "position": 8,
                        },
                        {
                            "link_type": "portfolio",
                            "url": "https://example.com",
                            "position": 2,
                        },
                    ],
                    "experiences": [
                        {
                            "employer": "Example Inc",
                            "role": "Engineer",
                            "is_current": True,
                            "position": 7,
                        }
                    ],
                    "projects": [
                        {
                            "name": "Interview Studio",
                            "technologies": ["Python", "Astro"],
                            "position": 4,
                        }
                    ],
                },
            )
            assert updated.status_code == 200
            body = updated.json()
            assert [item["position"] for item in body["links"]] == [0, 1]
            assert body["experiences"][0]["position"] == 0
            assert body["projects"][0]["technologies"] == ["Python", "Astro"]

            invalid_avatar = await client.post(
                "/api/v1/profile/avatar",
                files={"file": ("avatar.png", b"not-an-image", "image/png")},
            )
            assert invalid_avatar.status_code == 422
            avatar = await client.post(
                "/api/v1/profile/avatar",
                files={"file": ("avatar.png", avatar_bytes(), "image/png")},
            )
            assert avatar.status_code == 200
            assert avatar.json()["avatar_url"] == "/api/v1/profile/avatar"
            downloaded = await client.get("/api/v1/profile/avatar")
            assert downloaded.status_code == 200
            assert downloaded.headers["content-type"] == "image/png"

            invalid_cv = await client.post(
                "/api/v1/profile/cv/import",
                files={"file": ("resume.txt", b"hello", "text/plain")},
            )
            assert invalid_cv.status_code == 422
            imported = await client.post(
                "/api/v1/profile/cv/import",
                files={"file": ("resume.pdf", b"%PDF-fake", "application/pdf")},
            )
            assert imported.status_code == 200
            imported_body = imported.json()
            assert imported_body["full_name"] == "Taylor Example"
            assert imported_body["summary"] == "Imported summary"
            assert imported_body["skills"] == ["Python", "SQLite"]
            assert (
                await app.state.database.fetchone(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'profile_documents'
                    """
                )
                is None
            )

            unchanged = (await client.get("/api/v1/profile")).json()
            assert unchanged["full_name"] == "Manual Name"
            assert unchanged["summary"] == "Keep this manual summary"

            removed_avatar = await client.delete("/api/v1/profile/avatar")
            assert removed_avatar.status_code == 200
            assert removed_avatar.json()["avatar_url"] is None
