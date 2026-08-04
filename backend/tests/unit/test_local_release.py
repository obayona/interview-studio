from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from deployment.scripts.prepare_local_release import (
    current_versions,
    prepare_bundle,
    validate_version,
)


def _release_tree(root: Path, versions: tuple[str, str, str]) -> None:
    backend_version, frontend_version, environment_version = versions
    (root / "backend/app/core").mkdir(parents=True)
    (root / "backend/app/core/version.py").write_text(
        f'APP_VERSION = "{backend_version}"\n', encoding="utf-8"
    )
    (root / "frontend").mkdir()
    (root / "frontend/package.json").write_text(
        json.dumps({"version": frontend_version}), encoding="utf-8"
    )
    local = root / "deployment/local"
    (local / "scripts").mkdir(parents=True)
    (local / ".env.example").write_text(f"APP_VERSION={environment_version}\n", encoding="utf-8")
    (local / "compose.yml").write_text("services: {}\n", encoding="utf-8")
    (local / "README.md").write_text("local docs\n", encoding="utf-8")
    (local / "scripts/start-local.sh").write_text("#!/bin/sh\n", encoding="utf-8")


def test_release_versions_are_read_from_all_public_metadata(tmp_path: Path) -> None:
    _release_tree(tmp_path, ("1.2.3", "1.2.3", "1.2.3"))

    assert current_versions(tmp_path) == {
        "backend": "1.2.3",
        "frontend": "1.2.3",
        "local_environment": "1.2.3",
    }
    validate_version("1.2.3", tmp_path)


def test_release_rejects_invalid_or_mismatched_versions(tmp_path: Path) -> None:
    _release_tree(tmp_path, ("1.2.3", "1.2.4", "1.2.3"))

    with pytest.raises(ValueError, match=r"frontend=1\.2\.4"):
        validate_version("1.2.3", tmp_path)
    with pytest.raises(ValueError, match="semantic"):
        validate_version("latest", tmp_path)


def test_release_bundle_pins_metadata_and_required_operations(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    _release_tree(source, ("1.2.3", "1.2.3", "1.2.3"))
    output.mkdir()

    archive = prepare_bundle("1.2.3", output, source)

    assert archive.name == "interview-studio-local-1.2.3.tar.gz"
    with tarfile.open(archive) as bundle:
        names = set(bundle.getnames())
        prefix = "interview-studio-local-1.2.3"
        assert f"{prefix}/compose.yml" in names
        assert f"{prefix}/.env.example" in names
        assert f"{prefix}/scripts/start-local.sh" in names
