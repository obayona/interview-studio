from yoyo import step

__depends__ = {"001_phase2_core"}

steps = [
    step(
        """
        CREATE TABLE developer_profiles (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL DEFAULT '',
            headline TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            skills_json TEXT NOT NULL DEFAULT '[]',
            seniority TEXT NOT NULL DEFAULT '',
            availability TEXT NOT NULL DEFAULT '',
            avatar_blob BLOB,
            avatar_mime_type TEXT,
            avatar_size INTEGER,
            avatar_width INTEGER,
            avatar_height INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        "DROP TABLE IF EXISTS developer_profiles",
    ),
    step(
        """
        CREATE TABLE profile_links (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL REFERENCES developer_profiles(id) ON DELETE CASCADE,
            link_type TEXT NOT NULL,
            url TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(profile_id, link_type, url),
            UNIQUE(profile_id, position)
        )
        """,
        "DROP TABLE IF EXISTS profile_links",
    ),
    step(
        """
        CREATE INDEX idx_profile_links_profile
        ON profile_links(profile_id, position)
        """,
        "DROP INDEX IF EXISTS idx_profile_links_profile",
    ),
    step(
        """
        CREATE TABLE work_experiences (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL REFERENCES developer_profiles(id) ON DELETE CASCADE,
            employer TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT '',
            start_date TEXT,
            end_date TEXT,
            is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
            description TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(profile_id, position)
        )
        """,
        "DROP TABLE IF EXISTS work_experiences",
    ),
    step(
        """
        CREATE INDEX idx_work_experiences_profile
        ON work_experiences(profile_id, position)
        """,
        "DROP INDEX IF EXISTS idx_work_experiences_profile",
    ),
    step(
        """
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL REFERENCES developer_profiles(id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            technologies_json TEXT NOT NULL DEFAULT '[]',
            url TEXT NOT NULL DEFAULT '',
            repository_url TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(profile_id, position)
        )
        """,
        "DROP TABLE IF EXISTS projects",
    ),
    step(
        """
        CREATE INDEX idx_projects_profile
        ON projects(profile_id, position)
        """,
        "DROP INDEX IF EXISTS idx_projects_profile",
    ),
]
