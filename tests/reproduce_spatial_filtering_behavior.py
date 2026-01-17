
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
async def test_spatial_filtering_drops_no_coords(mock_template_service):
    """
    This test documents the current behavior:
    If a search includes a 'center_address' (parsed as location), the system applies spatial filtering.
    Entities that match the text query (e.g. 'Dublin') but lack coordinates (failed geocoding)
    are DROPPED by the spatial filter, resulting in 'No results found'.
    
    This explains why 'show customers in Dublin' might return nothing if the customer has no coords,
    whereas 'show customers' (no location) finds them.
    """
    # Setup DB
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # Create Business
        biz = Business(name="Test Biz")
        session.add(biz)
        await session.flush()
        
        executor = ToolExecutor(session, biz.id, "1234567890", mock_template_service)
        
        # Mock Geocoding
        # "Dublin" -> Resolves to coords
        # "Cathedral street 35, Dublin" -> Fails resolution (None)
        mock_geo = AsyncMock()
        
        async def side_effect(address):
            if address and "Cathedral" in address:
                return None, None, None, None, None # Failed address geocode
            if address and "Dublin" in address:
                return 53.3498, -6.2603, None, None, None # Success city geocode
            return None, None, None, None, None
            
        mock_geo.geocode.side_effect = side_effect
        executor.search_service.geocoding_service = mock_geo
        executor.geocoding_service = mock_geo
        
        # 1. Add Lead (Margaret)
        # Detailed address that fails geocoding => Latitude/Longitude will be None
        add_tool = AddLeadTool(
            name="Margaret",
            phone="086123123",
            location="Cathedral street 35, Dublin"
        )
        await executor.execute(add_tool)
        
        # 2. Search WITH location ("Dublin")
        # Logic: text search matches "Dublin" in address.
        # But center_address="Dublin" triggers spatial filter.
        # Margaret has no coords -> Dropped.
        extract_location_tool = SearchTool(
            query="Dublin",
            center_address="Dublin" 
        )
        result_spatial, _ = await executor.execute(extract_location_tool)
        
        # Expectation: Margaret NOT found due to missing coords
        assert "Margaret" not in result_spatial
        assert "No results found" in result_spatial
        
        # 3. Search WITHOUT location ("Dublin" as text only)
        # Logic: Matches text. No spatial filter.
        text_only_tool = SearchTool(
            query="Dublin",
            center_address=None,
            center_lat=None,
            center_lon=None
        )
        result_text, _ = await executor.execute(text_only_tool)
        
        # Expectation: Margaret FOUND
        assert "Margaret" in result_text

