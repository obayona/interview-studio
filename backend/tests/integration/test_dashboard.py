from __future__ import annotations

from pathlib import Path

import httpx

from backend.app.core.config import AppConfig
from backend.app.main import create_app
from backend.tests.integration.helpers import prepare_database
from backend.tests.integration.test_reports import QueueEvaluator, add_transcript, stage


async def test_dashboard_empty_onboarding_and_report_aggregates(tmp_path: Path) -> None:
    config = AppConfig(
        database_path=tmp_path / "dashboard.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            empty = (await client.get("/api/v1/dashboard")).json()
            assert empty["stats"]["process_count"] == 0
            assert empty["stats"]["average_score"] is None
            assert empty["recent_activity"] == []
            assert empty["onboarding"] == {
                "settings_configured": False,
                "profile_completed": False,
                "process_created": False,
                "interview_started": False,
            }

            await app.state.settings.update({"api_key": "test-key"})
            current = app.state.reports
            current._evaluator = QueueEvaluator([64, 86])
            created = (
                await client.post(
                    "/api/v1/processes",
                    json={
                        "title": "Platform role",
                        "target_role": "Platform engineer",
                        "job": {"kind": "text", "value": "Build reliable APIs."},
                        "stages": [stage()],
                    },
                )
            ).json()
            stage_id = created["stages"][0]["id"]
            attempts = []
            for _ in range(2):
                attempt = (
                    await client.post(
                        f"/api/v1/processes/{created['id']}/stages/{stage_id}/attempts"
                    )
                ).json()
                attempts.append(attempt)
                await add_transcript(app, attempt["id"])
                await app.state.attempts.mark_ended(attempt["id"], "explicit_end")
                response = await client.post(f"/api/v1/attempts/{attempt['id']}/report")
                assert response.status_code == 200

            dashboard = (await client.get("/api/v1/dashboard")).json()
            assert dashboard["stats"] == {
                "process_count": 1,
                "active_process_count": 1,
                "attempt_count": 2,
                "completed_attempt_count": 2,
                "evaluated_attempt_count": 2,
                "average_score": 75,
                "minimum_score": 64,
                "maximum_score": 86,
            }
            assert [point["score"] for point in dashboard["score_trend"]] == [64, 86]
            assert dashboard["strengths"] == [{"label": "Communication", "count": 2}]
            assert dashboard["weaknesses"] == [{"label": "Metrics", "count": 2}]
            assert dashboard["recent_activity"][0]["attempt_id"] == attempts[1]["id"]
            assert dashboard["onboarding"]["settings_configured"] is True
            assert dashboard["onboarding"]["process_created"] is True
            assert dashboard["onboarding"]["interview_started"] is True
