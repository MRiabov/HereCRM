import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from src.database import repair_sqlite_schema


@pytest.mark.asyncio
async def test_repair_sqlite_schema_adds_missing_business_columns(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            "CREATE TABLE businesses (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL)"
        )
        await conn.exec_driver_sql("INSERT INTO businesses (id, name) VALUES (1, 'Acme')")

    repaired = await repair_sqlite_schema(engine)

    assert ("businesses", "messenger_settings") in repaired

    async with engine.connect() as conn:
        result = await conn.exec_driver_sql(
            "SELECT messenger_settings, marketing_settings, workflow_distance_unit "
            "FROM businesses WHERE id = 1"
        )
        row = result.first()

    assert row == ("{}", "{}", "mi")

    await engine.dispose()
