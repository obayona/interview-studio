from __future__ import annotations

import base64
import sqlite3
from pathlib import Path

import pytest

from backend.app.core.secrets import SecretBox
from backend.cli.deployment_data import backup, restore, transfer_ownership
from deployment.scripts.validate_env import validate


def valid_environment() -> dict[str, str]:
    return {
        "DEPLOYMENT_ENV": "production",
        "DOMAIN": "studio.interviews.dev",
        "LETSENCRYPT_EMAIL": "owner@interviews.dev",
        "LETSENCRYPT_STAGING": "false",
        "APP_USERNAME": "owner",
        "APP_PASSWORD": "a-unique-password-longer-than-sixteen",
        "APP_ENCRYPTION_KEY": base64.b64encode(b"k" * 32).decode("ascii"),
        "APP_SESSION_LIFETIME_SECONDS": "3600",
    }


def test_deployment_environment_validation() -> None:
    assert validate(valid_environment()) == []
    invalid = valid_environment()
    invalid.update(
        {
            "DOMAIN": "https://example.com/path",
            "LETSENCRYPT_STAGING": "true",
            "APP_PASSWORD": "short",
            "APP_ENCRYPTION_KEY": "invalid",
        }
    )
    errors = validate(invalid)
    assert any("DOMAIN" in error for error in errors)
    assert any("staging" in error for error in errors)
    assert any("PASSWORD" in error for error in errors)
    assert any("ENCRYPTION_KEY" in error for error in errors)


def test_backup_and_restore_verify_database_and_secret(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    secret = tmp_path / "settings.key"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE example (value TEXT NOT NULL)")
    connection.execute("INSERT INTO example VALUES ('before')")
    connection.commit()
    connection.close()
    secret.write_bytes(b"s" * 32)

    backup_path = backup(database, secret, tmp_path / "backups")
    connection = sqlite3.connect(database)
    connection.execute("UPDATE example SET value = 'after'")
    connection.commit()
    connection.close()
    secret.write_bytes(b"x" * 32)

    restore(database, secret, backup_path)
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT value FROM example").fetchone()[0] == "before"
    connection.close()
    assert secret.read_bytes() == b"s" * 32

    (backup_path / "settings.key").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        restore(database, secret, backup_path)


def test_persisted_encryption_key_must_match_environment(tmp_path: Path) -> None:
    key_path = tmp_path / "settings.key"
    SecretBox(key_path, b"a" * 32)
    with pytest.raises(ValueError, match="does not match"):
        SecretBox(key_path, b"b" * 32)


def test_backup_owner_requires_numeric_user_and_group(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="UID:GID"):
        transfer_ownership(tmp_path, "current-user")


def test_restore_preserves_existing_runtime_ownership(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    secret = tmp_path / "settings.key"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE example (value TEXT NOT NULL)")
    connection.execute("INSERT INTO example VALUES ('before')")
    connection.commit()
    connection.close()
    secret.write_bytes(b"s" * 32)
    database_owner = (database.stat().st_uid, database.stat().st_gid)
    secret_owner = (secret.stat().st_uid, secret.stat().st_gid)
    backup_path = backup(database, secret, tmp_path / "backups")

    restore(database, secret, backup_path)

    assert (database.stat().st_uid, database.stat().st_gid) == database_owner
    assert (secret.stat().st_uid, secret.stat().st_gid) == secret_owner
