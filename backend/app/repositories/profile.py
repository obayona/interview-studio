from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import cast

from backend.app.core.database import SQLiteManager
from backend.app.domain.profile import (
    DeveloperProfile,
    ProfileLink,
    ProfileProject,
    ProfileUpdate,
    WorkExperience,
)

PROFILE_ID = "default"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ProfileRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def get(self) -> DeveloperProfile:
        async with self._database.transaction() as connection:
            row = self._get_profile(connection)
            return self._aggregate(connection, row)

    async def update(self, update: ProfileUpdate) -> DeveloperProfile:
        values = update.model_dump(exclude_unset=True, mode="json")
        async with self._database.transaction() as connection:
            scalar_fields = {
                key: value
                for key, value in values.items()
                if key
                in {
                    "full_name",
                    "headline",
                    "summary",
                    "location",
                    "email",
                    "phone",
                    "seniority",
                    "availability",
                }
            }
            if "skills" in values:
                scalar_fields["skills_json"] = json.dumps(values["skills"])
            if scalar_fields:
                scalar_fields["updated_at"] = utc_now()
                assignments = ", ".join(f"{key} = ?" for key in scalar_fields)
                connection.execute(
                    f"UPDATE developer_profiles SET {assignments} WHERE id = ?",
                    (*scalar_fields.values(), PROFILE_ID),
                )
            if update.links is not None:
                self._replace_links(connection, update.links)
            if update.experiences is not None:
                self._replace_experiences(connection, update.experiences)
            if update.projects is not None:
                self._replace_projects(connection, update.projects)
            row = self._get_profile(connection)
            return self._aggregate(connection, row)

    async def set_avatar(self, content: bytes, mime_type: str, width: int, height: int) -> None:
        async with self._database.transaction() as connection:
            connection.execute(
                """
                UPDATE developer_profiles
                SET avatar_blob = ?, avatar_mime_type = ?, avatar_size = ?,
                    avatar_width = ?, avatar_height = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    content,
                    mime_type,
                    len(content),
                    width,
                    height,
                    utc_now(),
                    PROFILE_ID,
                ),
            )

    async def get_avatar(self) -> tuple[bytes, str] | None:
        row = await self._database.fetchone(
            """
            SELECT avatar_blob, avatar_mime_type
            FROM developer_profiles
            WHERE id = ? AND avatar_blob IS NOT NULL
            """,
            (PROFILE_ID,),
        )
        if row is None:
            return None
        return bytes(row["avatar_blob"]), str(row["avatar_mime_type"])

    async def delete_avatar(self) -> None:
        async with self._database.transaction() as connection:
            connection.execute(
                """
                UPDATE developer_profiles
                SET avatar_blob = NULL, avatar_mime_type = NULL, avatar_size = NULL,
                    avatar_width = NULL, avatar_height = NULL, updated_at = ?
                WHERE id = ?
                """,
                (utc_now(), PROFILE_ID),
            )

    def _get_profile(self, connection: sqlite3.Connection) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM developer_profiles WHERE id = ?", (PROFILE_ID,)
        ).fetchone()
        if row is None:
            raise RuntimeError("The default profile startup fixture has not been applied")
        return cast(sqlite3.Row, row)

    def _aggregate(self, connection: sqlite3.Connection, row: sqlite3.Row) -> DeveloperProfile:
        links = connection.execute(
            "SELECT * FROM profile_links WHERE profile_id = ? ORDER BY position",
            (PROFILE_ID,),
        ).fetchall()
        experiences = connection.execute(
            "SELECT * FROM work_experiences WHERE profile_id = ? ORDER BY position",
            (PROFILE_ID,),
        ).fetchall()
        projects = connection.execute(
            "SELECT * FROM projects WHERE profile_id = ? ORDER BY position",
            (PROFILE_ID,),
        ).fetchall()
        return DeveloperProfile(
            id=str(row["id"]),
            full_name=str(row["full_name"]),
            headline=str(row["headline"]),
            summary=str(row["summary"]),
            location=str(row["location"]),
            email=str(row["email"]),
            phone=str(row["phone"]),
            skills=json.loads(str(row["skills_json"])),
            seniority=str(row["seniority"]),
            availability=str(row["availability"]),
            links=[
                ProfileLink(
                    id=item["id"],
                    link_type=item["link_type"],
                    url=item["url"],
                    position=item["position"],
                )
                for item in links
            ],
            experiences=[
                WorkExperience(
                    id=item["id"],
                    employer=item["employer"],
                    role=item["role"],
                    start_date=item["start_date"],
                    end_date=item["end_date"],
                    is_current=bool(item["is_current"]),
                    description=item["description"],
                    position=item["position"],
                )
                for item in experiences
            ],
            projects=[
                ProfileProject(
                    id=item["id"],
                    name=item["name"],
                    role=item["role"],
                    description=item["description"],
                    technologies=json.loads(str(item["technologies_json"])),
                    url=item["url"] or None,
                    repository_url=item["repository_url"] or None,
                    position=item["position"],
                )
                for item in projects
            ],
            avatar_url=("/api/v1/profile/avatar" if row["avatar_blob"] is not None else None),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _replace_links(self, connection: sqlite3.Connection, links: list[ProfileLink]) -> None:
        connection.execute("DELETE FROM profile_links WHERE profile_id = ?", (PROFILE_ID,))
        now = utc_now()
        connection.executemany(
            """
            INSERT INTO profile_links (
                id, profile_id, link_type, url, position, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.id,
                    PROFILE_ID,
                    item.link_type,
                    str(item.url),
                    position,
                    now,
                    now,
                )
                for position, item in enumerate(links)
            ],
        )

    def _replace_experiences(
        self, connection: sqlite3.Connection, experiences: list[WorkExperience]
    ) -> None:
        connection.execute("DELETE FROM work_experiences WHERE profile_id = ?", (PROFILE_ID,))
        now = utc_now()
        connection.executemany(
            """
            INSERT INTO work_experiences (
                id, profile_id, employer, role, start_date, end_date, is_current,
                description, position, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.id,
                    PROFILE_ID,
                    item.employer,
                    item.role,
                    item.start_date.isoformat() if item.start_date else None,
                    item.end_date.isoformat() if item.end_date else None,
                    int(item.is_current),
                    item.description,
                    position,
                    now,
                    now,
                )
                for position, item in enumerate(experiences)
            ],
        )

    def _replace_projects(
        self, connection: sqlite3.Connection, projects: list[ProfileProject]
    ) -> None:
        connection.execute("DELETE FROM projects WHERE profile_id = ?", (PROFILE_ID,))
        now = utc_now()
        connection.executemany(
            """
            INSERT INTO projects (
                id, profile_id, name, role, description, technologies_json,
                url, repository_url, position, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.id,
                    PROFILE_ID,
                    item.name,
                    item.role,
                    item.description,
                    json.dumps(item.technologies),
                    str(item.url) if item.url else "",
                    str(item.repository_url) if item.repository_url else "",
                    position,
                    now,
                    now,
                )
                for position, item in enumerate(projects)
            ],
        )
