import argparse
from pathlib import Path

from backend.app.core.migrations import migrate_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Interview Studio migrations")
    parser.add_argument("database", type=Path)
    parser.add_argument(
        "--migrations",
        type=Path,
        default=Path(__file__).parents[1] / "migrations",
    )
    arguments = parser.parse_args()
    migrate_database(arguments.database, arguments.migrations)


if __name__ == "__main__":
    main()
