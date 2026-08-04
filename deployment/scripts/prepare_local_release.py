from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
from pathlib import Path

SEMANTIC_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ROOT = Path(__file__).resolve().parents[2]


def current_versions(root: Path = ROOT) -> dict[str, str]:
    namespace: dict[str, str] = {}
    exec((root / "backend/app/core/version.py").read_text(encoding="utf-8"), namespace)
    frontend = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))
    environment = {}
    for line in (root / "deployment/local/.env.example").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            environment[key.strip()] = value.strip()
    return {
        "backend": namespace["APP_VERSION"],
        "frontend": frontend["version"],
        "local_environment": environment["APP_VERSION"],
    }


def validate_version(version: str, root: Path = ROOT) -> None:
    if not SEMANTIC_VERSION.fullmatch(version):
        raise ValueError("Release version must use semantic form such as 1.0.0")
    mismatches = {name: value for name, value in current_versions(root).items() if value != version}
    if mismatches:
        details = ", ".join(f"{name}={value}" for name, value in mismatches.items())
        raise ValueError(f"Release metadata does not match {version}: {details}")


def prepare_bundle(version: str, destination: Path, root: Path = ROOT) -> Path:
    validate_version(version, root)
    bundle = destination / f"interview-studio-local-{version}"
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "scripts").mkdir(parents=True)
    shutil.copy2(root / "deployment/local/compose.yml", bundle / "compose.yml")
    shutil.copy2(root / "deployment/local/.env.example", bundle / ".env.example")
    shutil.copy2(root / "deployment/local/README.md", bundle / "README.md")
    for source in sorted((root / "deployment/local/scripts").iterdir()):
        if source.is_file():
            shutil.copy2(source, bundle / "scripts" / source.name)
    archive = destination / f"interview-studio-local-{version}.tar.gz"
    if archive.exists():
        archive.unlink()
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as output:
        output.add(bundle, arcname=bundle.name, filter=_normalized_tar_info)
    return archive


def _normalized_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = 0
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and build a local release bundle")
    parser.add_argument("version", help="Semantic version without the v tag prefix")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        validate_version(arguments.version)
        if arguments.output:
            arguments.output.mkdir(parents=True, exist_ok=True)
            print(prepare_bundle(arguments.version, arguments.output))
        else:
            print(f"Release metadata is synchronized at {arguments.version}.")
    except ValueError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
