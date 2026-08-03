from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def backup(database: Path, secret: Path, destination: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = destination / timestamp
    target.mkdir(parents=True, exist_ok=False)
    database_target = target / "interview_studio.sqlite3"
    secret_target = target / "settings.key"
    source = sqlite3.connect(database)
    output = sqlite3.connect(database_target)
    try:
        source.backup(output)
    finally:
        output.close()
        source.close()
    shutil.copy2(secret, secret_target)
    secret_target.chmod(0o600)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "database_sha256": _digest(database_target),
        "secret_sha256": _digest(secret_target),
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


def restore(database: Path, secret: Path, source: Path) -> None:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    database_source = source / "interview_studio.sqlite3"
    secret_source = source / "settings.key"
    expected: dict[str, Any] = manifest
    if _digest(database_source) != expected.get("database_sha256"):
        raise ValueError("Backup database checksum does not match its manifest")
    if _digest(secret_source) != expected.get("secret_sha256"):
        raise ValueError("Backup settings key checksum does not match its manifest")
    database.parent.mkdir(parents=True, exist_ok=True)
    secret.parent.mkdir(parents=True, exist_ok=True)
    database_temp = database.with_suffix(".restore.tmp")
    secret_temp = secret.with_suffix(".restore.tmp")
    shutil.copy2(database_source, database_temp)
    shutil.copy2(secret_source, secret_temp)
    secret_temp.chmod(0o600)
    os.replace(database_temp, database)
    os.replace(secret_temp, secret)


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up or restore deployment data")
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("--database", type=Path, default=Path("/data/interview_studio.sqlite3"))
    parser.add_argument("--secret", type=Path, default=Path("/secrets/settings.key"))
    parser.add_argument("--backup-dir", type=Path, default=Path("/backups"))
    parser.add_argument("--source", type=Path)
    arguments = parser.parse_args()
    if arguments.action == "backup":
        print(backup(arguments.database, arguments.secret, arguments.backup_dir))
    else:
        if arguments.source is None:
            parser.error("--source is required when restoring")
        restore(arguments.database, arguments.secret, arguments.source)


if __name__ == "__main__":
    main()
