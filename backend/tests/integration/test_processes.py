from __future__ import annotations

from pathlib import Path

import httpx

from backend.app.application.processes import ProcessService, SafeContentFetcher
from backend.app.core.config import AppConfig
from backend.app.core.errors import ApplicationError
from backend.app.domain.processes import ImportPreview
from backend.app.main import create_app
from backend.tests.integration.helpers import prepare_database


def stage(stage_type: str, enabled: bool = True) -> dict[str, object]:
    return {
        "stage_type": stage_type,
        "enabled": enabled,
        "configuration": {
            "difficulty": "senior",
            "interviewer_profile": "cto",
            "user_instructions": "",
            "language": "English",
            "topics": ["architecture"],
            "limits": {
                "max_questions": 6,
                "max_duration_minutes": 25,
                "follow_up_questions_per_topic": 2,
            },
        },
    }


async def test_process_crud_stage_configuration_and_repeated_attempts(
    tmp_path: Path,
) -> None:
    config = AppConfig(
        database_path=tmp_path / "processes.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/processes",
                json={
                    "title": "Backend role",
                    "company_name": "Example Co",
                    "target_role": "Senior Backend Engineer",
                    "job": {"kind": "text", "value": "Build reliable APIs."},
                    "company": {"kind": "text", "value": "Developer tools."},
                    "stages": [
                        stage("screening"),
                        stage("behavioral", False),
                        stage("system_design"),
                    ],
                },
            )
            assert created.status_code == 201
            process = created.json()
            assert [item["status"] for item in process["stages"]] == [
                "not_started",
                "skipped",
                "not_started",
            ]
            assert process["stages"][2]["configuration"]["difficulty"] == "senior"

            listed = (await client.get("/api/v1/processes")).json()
            assert listed[0]["stage_count"] == 3
            assert listed[0]["attempt_count"] == 0

            process_id = process["id"]
            stage_id = process["stages"][0]["id"]
            skipped_id = process["stages"][1]["id"]
            await app.state.settings.update({"stt_enabled": "true", "tts_enabled": "true"})
            disabled = await client.post(
                f"/api/v1/processes/{process_id}/stages/{skipped_id}/attempts"
            )
            assert disabled.status_code == 409
            first = await client.post(f"/api/v1/processes/{process_id}/stages/{stage_id}/attempts")
            second = await client.post(f"/api/v1/processes/{process_id}/stages/{stage_id}/attempts")
            assert first.json()["attempt_number"] == 1
            assert second.json()["attempt_number"] == 2
            assert first.json()["id"] != second.json()["id"]

            assert await app.state.attempts.media_preferences(first.json()["id"]) == {
                "speech_to_text": True,
                "text_to_speech": True,
            }
            await app.state.attempts.set_media_preference(
                first.json()["id"], "speech_to_text", False
            )
            assert await app.state.attempts.media_preferences(first.json()["id"]) == {
                "speech_to_text": False,
                "text_to_speech": True,
            }
            await app.state.attempts.mark_started(first.json()["id"])
            await app.state.attempts.mark_paused(first.json()["id"])
            detail = (await client.get(f"/api/v1/processes/{process_id}")).json()
            assert len(detail["stages"][0]["attempts"]) == 2
            assert detail["stages"][0]["attempts"][0]["status"] == "paused"
            assert detail["stages"][0]["status"] == "in_progress"

            deleted_attempt = await client.delete(f"/api/v1/attempts/{first.json()['id']}")
            assert deleted_attempt.status_code == 204
            detail = (await client.get(f"/api/v1/processes/{process_id}")).json()
            assert [item["attempt_number"] for item in detail["stages"][0]["attempts"]] == [2]
            assert (
                await client.delete(f"/api/v1/attempts/{first.json()['id']}")
            ).status_code == 404

            reordered = [
                {
                    "id": item["id"],
                    "stage_type": item["stage_type"],
                    "enabled": item["enabled"],
                    "configuration": item["configuration"],
                }
                for item in reversed(detail["stages"])
            ]
            updated = await client.patch(
                f"/api/v1/processes/{process_id}",
                json={"title": "Updated backend role", "stages": reordered},
            )
            assert updated.json()["title"] == "Updated backend role"
            assert updated.json()["stages"][2]["id"] == stage_id

            removed = await client.delete(f"/api/v1/processes/{process_id}")
            assert removed.status_code == 204
            assert (await client.get(f"/api/v1/processes/{process_id}")).status_code == 404


class FakeFetcher(SafeContentFetcher):
    async def fetch(self, url: str) -> ImportPreview:
        return ImportPreview(url=url, content="Normalized imported content")


async def test_url_and_text_sources_use_the_same_normalized_fields(
    tmp_path: Path,
) -> None:
    config = AppConfig(
        database_path=tmp_path / "imports.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        current = app.state.processes
        app.state.processes = ProcessService(
            current._repository,
            current._profiles,
            current._settings,
            FakeFetcher(),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            preview = await client.post(
                "/api/v1/processes/import-preview",
                json={"url": "https://example.com/job"},
            )
            assert preview.json()["content"] == "Normalized imported content"
            created = await client.post(
                "/api/v1/processes",
                json={
                    "title": "Imported role",
                    "target_role": "Engineer",
                    "job": {"kind": "url", "value": "https://example.com/job"},
                    "stages": [stage("technical")],
                },
            )
            assert created.json()["job_description"] == "Normalized imported content"
            assert created.json()["job_source_url"] == "https://example.com/job"


async def test_safe_fetcher_rejects_local_network_urls() -> None:
    try:
        await SafeContentFetcher().fetch("http://127.0.0.1/private")
    except ApplicationError as error:
        assert error.code == "process_import_failed"
        assert "Private" in error.message
    else:
        raise AssertionError("Local URLs must be rejected")
