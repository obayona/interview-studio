import argparse
import sqlite3
from pathlib import Path

from backend.app.core.fixtures import load_fixtures


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Interview Studio SQL fixtures")
    parser.add_argument("database", type=Path)
    arguments = parser.parse_args()
    connection = sqlite3.connect(arguments.database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            load_fixtures(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
