from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_local_compose_is_loopback_only_and_version_pinned() -> None:
    compose = (ROOT / "deployment/local/compose.yml").read_text(encoding="utf-8")

    assert "127.0.0.1:${LOCAL_PORT:-8080}:8080" in compose
    assert "ghcr.io/obayona/interview-studio-backend:${APP_VERSION" in compose
    assert "ghcr.io/obayona/interview-studio-web:${APP_VERSION" in compose
    assert 'APP_SERVER_MODE: "false"' in compose
    assert "0.0.0.0:${LOCAL_PORT" not in compose
    assert "certbot" not in compose


def test_local_operations_retain_data_unless_explicitly_confirmed() -> None:
    scripts = ROOT / "deployment/local/scripts"
    posix = (scripts / "uninstall-local.sh").read_text(encoding="utf-8")
    powershell = (scripts / "Uninstall-Local.ps1").read_text(encoding="utf-8")

    assert 'if [ "${1:-}" != "--delete-data" ]' in posix
    assert 'if [ "$confirmation" != "DELETE" ]' in posix
    assert "down --volumes" in posix
    assert "if (-not $DeleteData)" in powershell
    assert '$confirmation -ne "DELETE"' in powershell
    assert "down --volumes" in powershell


def test_update_stops_writes_before_migration() -> None:
    scripts = ROOT / "deployment/local/scripts"
    posix = (scripts / "update-local.sh").read_text(encoding="utf-8")
    powershell = (scripts / "Update-Local.ps1").read_text(encoding="utf-8")

    assert posix.index("stop backend web") < posix.index("run --rm migrate")
    assert powershell.index("stop backend web") < powershell.index("run --rm migrate")


def test_launchers_create_the_backup_bind_as_the_local_user() -> None:
    scripts = ROOT / "deployment/local/scripts"
    posix = (scripts / "common.sh").read_text(encoding="utf-8")
    powershell = (scripts / "Common.ps1").read_text(encoding="utf-8")

    assert 'mkdir -p "$BACKUP_DIR"' in posix
    assert "export BACKUP_DIR" in posix
    assert "New-Item -ItemType Directory" in powershell
    assert "$env:BACKUP_DIR = $values.BACKUP_DIR" in powershell
    assert "LOCAL_BACKUP_UID=$(id -u)" in posix


def test_backup_tool_can_read_volumes_and_returns_files_to_the_local_user() -> None:
    compose = (ROOT / "deployment/local/compose.yml").read_text(encoding="utf-8")

    backup_section = compose.split("  backup:", 1)[1].split("  restore:", 1)[0]
    restore_section = compose.split("  restore:", 1)[1]
    assert 'user: "0:0"' in backup_section
    assert "--owner" in backup_section
    assert "LOCAL_BACKUP_UID" in backup_section
    assert 'user: "0:0"' in restore_section
