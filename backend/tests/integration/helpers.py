from backend.app.core.config import AppConfig
from backend.app.core.database import SQLiteManager
from backend.app.core.fixtures import load_fixtures
from backend.app.core.migrations import migrate_database


async def prepare_database(config: AppConfig) -> None:
    migrate_database(config.database_path, config.migrations_path)
    database = SQLiteManager(config.database_path, config.migrations_path)
    await database.start()
    async with database.transaction() as connection:
        load_fixtures(connection)
    await database.close()
