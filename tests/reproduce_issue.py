import pytest
from unittest.mock import AsyncMock
from src.tool_executor import ToolExecutor
from src.uimodels import AddLeadTool, SearchTool
from src.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def mock_template_service():
    return TemplateService()


@pytest.mark.asyncio
async def test_reproduce_dublin_search_failure(mock_template_service):
    # Setup DB
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with SessionLocal() as session:
        # Create Business
        biz = Business(name="Test Biz")
        session.add(biz)
        await session.flush()

        executor = ToolExecutor(session, biz.id, "1234567890", mock_template_service)

        # Mock Geocoding to FAIL for the address, but SUCCEED for "Dublin"
        # This simulates a scenario where specific address lookup failed, but city lookup works
        mock_geo = AsyncMock()

        async def side_effect(address):
            if "Cathedral" in address:
                return None, None, None, None, None  # Failed address geocode
            if "Dublin" in address:
                return 53.3498, -6.2603, None, None, None  # Success city geocode
            return None, None, None, None, None

        mock_geo.geocode.side_effect = side_effect
        executor.search_service.geocoding_service = mock_geo

        # 1. Add Lead (Margaret)
        # Detailed address that fails geocoding
        add_tool = AddLeadTool(
            name="Margaret", phone="086123123", location="Cathedral street 35, Dublin"
        )
        await executor.execute(add_tool)

        # 2. Search "in Dublin"
        # Scenario A: LLM maps "in Dublin" to query="Dublin" AND center_address="Dublin"
        # Because we used "in", it implies location.
        search_tool = SearchTool(
            query="Dublin",
            center_address="Dublin",
            # radius defaults to 200m in SearchService if center_address provided (and resolved)
        )

        result, _ = await executor.execute(search_tool)

        # If the bug exists, result should be "No results found" because:
        # - Margaret matches text "Dublin"
        # - spatial filter is applied (center_lat is set)
        # - Margaret has NO lat/lon (geocode failed)
        # - Spatial filter drops Margaret

        print(f"\nResult for Scenario A: {result}")

        if "Margaret" not in result:
            pytest.fail(
                "Scenario A Failed: Margaret should be found by text match even if geocoding failed for her specific address, or at least we should understand why she is dropped."
            )
