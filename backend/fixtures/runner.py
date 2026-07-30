import argparse
import sqlite3
from pathlib import Path

from backend.fixtures import browser_harness, default_profile, default_settings

FIXTURES = (
    default_settings.apply,
    default_profile.apply,
    browser_harness.apply,
)


def run_fixtures(connection: sqlite3.Connection) -> None:
    for fixture in FIXTURES:
        fixture(connection)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Interview Studio SQL fixtures")
    parser.add_argument("database", type=Path)
    arguments = parser.parse_args()
    connection = sqlite3.connect(arguments.database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            run_fixtures(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
