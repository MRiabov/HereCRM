
import pytest
from unittest.mock import AsyncMock
from src.tool_executor import ToolExecutor
from src.uimodels import EditCustomerTool, AddLeadTool, SearchTool
from src.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, User
from sqlalchemy import select

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
def mock_template_service():
    return TemplateService()

@pytest.mark.asyncio
async def test_edit_customer_regeocodes(mock_template_service):
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
        
        user = User(phone_number="1234567890", business_id=biz.id)
        session.add(user)
        await session.flush()
        
        executor = ToolExecutor(session, biz.id, user.id, user.phone_number, mock_template_service)
        
        # Mock Geocoding
        # Initial: "Bad Address" -> None
        # Updated: "Dublin" -> Coords
        mock_geo = AsyncMock()
        
        async def side_effect(address, **kwargs):
            if address == "Bad Address":
                return None, None, None, None, None, None, "Bad Address"
            if address == "Dublin":
                return 53.3498, -6.2603, "Street", "Dublin", "Ireland", "D01", "Street, Dublin, Ireland, D01"
            return None, None, None, None, None, None, address
            
        mock_geo.geocode.side_effect = side_effect
        executor.geocoding_service = mock_geo
        executor.search_service.geocoding_service = mock_geo

        # 1. Add Lead with Bad Address
        add_tool = AddLeadTool(
            name="Margaret",
            phone="086123123",
            location="Bad Address"
        )
        await executor.execute(add_tool)
        
        # Verify NO coords
        res = await session.execute(select(Customer).where(Customer.name == "Margaret"))
        cust = res.scalar_one()
        assert cust.latitude is None
        assert cust.longitude is None
        
        # 2. Edit Customer to "Dublin"
        edit_tool = EditCustomerTool(
            query="Margaret",
            location="Dublin"
        )
        await executor.execute(edit_tool)
        
        # 3. Verify Coords UPDATED
        await session.refresh(cust)
        assert cust.latitude == 53.3498
        assert cust.longitude == -6.2603
        assert cust.city == "Dublin"
        
        # 4. Search with Spatial Filter should now FIND her
        search_tool = SearchTool(
            query="Margaret",
            center_address="Dublin" 
        )
        result, _ = await executor.execute(search_tool)
        assert "Margaret" in result
