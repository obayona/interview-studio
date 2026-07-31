import sqlite3

from backend.fixtures import default_profile, default_settings

FIXTURES = (
    default_settings.apply,
    default_profile.apply,
)


def load_fixtures(connection: sqlite3.Connection) -> None:
    for fixture in FIXTURES:
        fixture(connection)
