from __future__ import annotations

import argparse
import base64
import binascii
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

DOMAIN_PATTERN = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PLACEHOLDERS = ("example.com", "replace-with", "change-me", "changeme")


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"Invalid .env assignment on line {line_number}")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def validate(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    required = (
        "DEPLOYMENT_ENV",
        "DOMAIN",
        "LETSENCRYPT_EMAIL",
        "LETSENCRYPT_STAGING",
        "APP_USERNAME",
        "APP_PASSWORD",
        "APP_ENCRYPTION_KEY",
    )
    for key in required:
        if not values.get(key):
            errors.append(f"{key} is required")

    domain = values.get("DOMAIN", "").lower()
    if domain and not DOMAIN_PATTERN.fullmatch(domain):
        errors.append("DOMAIN must be one public DNS hostname without a scheme or path")
    if any(placeholder in domain for placeholder in PLACEHOLDERS):
        errors.append("DOMAIN still contains an example or placeholder value")

    email = values.get("LETSENCRYPT_EMAIL", "")
    if email and not EMAIL_PATTERN.fullmatch(email):
        errors.append("LETSENCRYPT_EMAIL is not a valid email address")
    if any(placeholder in email.lower() for placeholder in PLACEHOLDERS):
        errors.append("LETSENCRYPT_EMAIL still contains an example or placeholder value")

    environment = values.get("DEPLOYMENT_ENV", "")
    if environment not in {"production", "staging"}:
        errors.append("DEPLOYMENT_ENV must be production or staging")
    staging = values.get("LETSENCRYPT_STAGING", "")
    if staging not in {"true", "false"}:
        errors.append("LETSENCRYPT_STAGING must be true or false")
    if environment == "production" and staging == "true":
        errors.append("Production deployments cannot use the Let's Encrypt staging issuer")

    username = values.get("APP_USERNAME", "")
    if not 1 <= len(username) <= 128:
        errors.append("APP_USERNAME must contain between 1 and 128 characters")
    password = values.get("APP_PASSWORD", "")
    if len(password) < 16:
        errors.append("APP_PASSWORD must contain at least 16 characters")
    if any(placeholder in password.lower() for placeholder in PLACEHOLDERS):
        errors.append("APP_PASSWORD still contains a placeholder value")
    if password and (password == username or password.lower() == domain):
        errors.append("APP_PASSWORD must not match the username or domain")

    encoded_key = values.get("APP_ENCRYPTION_KEY", "")
    if encoded_key:
        try:
            key = base64.b64decode(encoded_key, validate=True)
        except (binascii.Error, ValueError):
            key = b""
        if len(key) != 32:
            errors.append("APP_ENCRYPTION_KEY must be base64 for exactly 32 random bytes")

    lifetime = values.get("APP_SESSION_LIFETIME_SECONDS", "86400")
    try:
        if int(lifetime) < 300:
            errors.append("APP_SESSION_LIFETIME_SECONDS must be at least 300")
    except ValueError:
        errors.append("APP_SESSION_LIFETIME_SECONDS must be an integer")
    return errors


def host_port_in_use(port: int) -> bool:
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            content = Path(table).read_text(encoding="utf-8")
        except OSError:
            continue
        for line in content.splitlines()[1:]:
            fields = line.split()
            if len(fields) < 4:
                continue
            if fields[3] != "0A":  # 0A is TCP_LISTEN
                continue
            if int(fields[1].rsplit(":", 1)[1], 16) == port:
                return True
    return False


def installation_errors(env_path: Path, compose_file: Path | None = None) -> list[str]:
    errors: list[str] = []
    mode = stat.S_IMODE(env_path.stat().st_mode)
    if mode & 0o077:
        errors.append(".env must not be accessible by group or other users; run chmod 600 .env")
    if shutil.which("docker") is None:
        errors.append("Docker is not installed or not available on PATH")
    else:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            errors.append("Docker Compose v2 is unavailable")
    nginx_running = False
    if shutil.which("docker") is not None:
        cmd = ["docker", "compose"]
        if compose_file is not None:
            cmd += ["-f", str(compose_file)]
        cmd += ["ps", "-q", "nginx"]
        running_nginx = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            text=True,
        )
        nginx_running = bool(running_nginx.stdout.strip())
    if not nginx_running:
        for port in (80, 443):
            if host_port_in_use(port):
                errors.append(f"Host port {port} is already in use")
    backup_dir = Path(os.path.expanduser(read_env(env_path).get("BACKUP_DIR", "./backups")))
    backup_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(backup_dir, os.W_OK):
        errors.append(f"Backup directory is not writable: {backup_dir}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Interview Studio deployment settings")
    parser.add_argument("path", nargs="?", type=Path, default=Path(".env"))
    parser.add_argument("--installation", action="store_true")
    parser.add_argument("--compose-file", type=Path, default=None)
    arguments = parser.parse_args()
    if not arguments.path.is_file():
        raise SystemExit(f"Environment file not found: {arguments.path}")
    try:
        values = read_env(arguments.path)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    errors = validate(values)
    if arguments.installation:
        errors.extend(installation_errors(arguments.path, arguments.compose_file))
    if errors:
        raise SystemExit("Invalid deployment configuration:\n- " + "\n- ".join(errors))
    print("Deployment configuration is valid.")


if __name__ == "__main__":
    main()
