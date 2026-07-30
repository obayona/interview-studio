import sqlite3

from backend.fixtures import browser_harness, default_profile, default_settings

FIXTURES = (
    default_settings.apply,
    default_profile.apply,
    browser_harness.apply,
)


def load_fixtures(connection: sqlite3.Connection) -> None:
    for fixture in FIXTURES:
        fixture(connection)
