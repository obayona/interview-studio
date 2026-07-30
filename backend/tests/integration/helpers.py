from backend.app.core.config import AppConfig
from backend.app.core.database import SQLiteManager
from backend.fixtures.runner import run_fixtures


async def prepare_database(config: AppConfig) -> None:
    database = SQLiteManager(config.database_path, config.migrations_path)
    await database.start()
    async with database.transaction() as connection:
        run_fixtures(connection)
    await database.close()
