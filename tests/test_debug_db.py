import os
import pytest
from src.database import engine


@pytest.mark.asyncio
async def test_database_url():
    print(f"\nDATABASE_URL in env: {os.environ.get('DATABASE_URL')}")
    print(f"Engine URL: {engine.url}")
    assert "memory" in str(engine.url)
