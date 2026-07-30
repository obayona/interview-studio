from pathlib import Path

from yoyo import get_backend, read_migrations


def migrate_database(database_path: Path, migrations_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    backend = get_backend(f"sqlite:///{database_path}")
    migrations = read_migrations(str(migrations_path))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
