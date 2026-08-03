from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from langchain_core.messages import HumanMessage

from backend.app.core.config import AppConfig
from backend.app.infrastructure.json_codec import StrictJsonCodec
from backend.app.main import create_app
from backend.tests.integration.helpers import prepare_database


async def test_versioned_scene_and_png_snapshot_persistence(tmp_path: Path) -> None:
    config = AppConfig(
        database_path=tmp_path / "system-design.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            process = (
                await client.post(
                    "/api/v1/processes",
                    json={
                        "title": "System design practice",
                        "target_role": "Staff Engineer",
                        "job": {"kind": "text", "value": "Design distributed systems."},
                        "stages": [
                            {
                                "stage_type": "system_design",
                                "configuration": {},
                            },
                            {
                                "stage_type": "screening",
                                "configuration": {},
                            },
                        ],
                    },
                )
            ).json()
            attempt = (
                await client.post(
                    f"/api/v1/processes/{process['id']}/stages/"
                    f"{process['stages'][0]['id']}/attempts"
                )
            ).json()
            attempt_id = attempt["id"]
            screening_attempt = (
                await client.post(
                    f"/api/v1/processes/{process['id']}/stages/"
                    f"{process['stages'][1]['id']}/attempts"
                )
            ).json()
            unavailable = await client.get(f"/api/v1/system-design/{screening_attempt['id']}")
            assert unavailable.status_code == 409
            assert unavailable.json()["code"] == "not_system_design_attempt"

            empty = await client.get(f"/api/v1/system-design/{attempt_id}")
            assert empty.status_code == 200
            assert empty.json()["scene_version"] == 0
            assert empty.json()["scene"]["elements"] == []

            scene = {
                "type": "excalidraw",
                "version": 2,
                "elements": [{"id": "api", "type": "rectangle"}],
                "appState": {"viewBackgroundColor": "#ffffff"},
                "files": {},
            }
            saved = await client.put(
                f"/api/v1/system-design/{attempt_id}",
                json={"expected_version": 0, "scene": scene},
            )
            assert saved.status_code == 200
            assert saved.json()["scene_version"] == 1

            stale = await client.put(
                f"/api/v1/system-design/{attempt_id}",
                json={"expected_version": 0, "scene": scene},
            )
            assert stale.status_code == 409
            assert stale.json()["code"] == "stale_scene_version"

            png = b"\x89PNG\r\n\x1a\nwhiteboard"
            snapshot = await client.post(
                f"/api/v1/system-design/{attempt_id}/snapshots",
                data={"scene_version": "1", "reason": "explicit"},
                files={"image": ("whiteboard.png", png, "image/png")},
            )
            assert snapshot.status_code == 201
            snapshot_body = snapshot.json()
            assert snapshot_body["scene_version"] == 1
            image = await client.get(snapshot_body["image_url"])
            assert image.content == png
            assert image.headers["content-type"] == "image/png"

            message_id = str(uuid4())
            stored_message_id = str(uuid4())
            async with app.state.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO interview_messages (
                        id, attempt_id, langgraph_message_id, sequence, role,
                        message_type, content_json, created_at
                    ) VALUES (?, ?, ?, 0, 'human', 'human', ?, ?)
                    """,
                    (
                        stored_message_id,
                        attempt_id,
                        message_id,
                        StrictJsonCodec().dumps_message(
                            HumanMessage(content="My design", id=message_id)
                        ),
                        datetime.now(UTC).isoformat(),
                    ),
                )
            associated = await app.state.system_design.associate_snapshot(
                attempt_id, snapshot_body["id"], "An API connects to a database."
            )
            assert associated.transcript_message_id == message_id
            assert associated.observation == "An API connects to a database."

            reloaded = await client.get(f"/api/v1/system-design/{attempt_id}")
            assert reloaded.json()["scene"] == scene
            assert len(reloaded.json()["snapshots"]) == 1
            assert reloaded.json()["snapshots"][0]["transcript_message_id"] == message_id

            deleted = await client.delete(f"/api/v1/processes/{process['id']}")
            assert deleted.status_code == 204
            assert (
                await app.state.database.fetchone(
                    "SELECT 1 FROM system_design_sessions WHERE attempt_id = ?",
                    (attempt_id,),
                )
                is None
            )
