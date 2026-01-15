import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Customer
from src.repositories import CustomerRepository, normalize_phone

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_customer_phone_deduplication(db_session: AsyncSession):
    repo = CustomerRepository(db_session)
    business_id = 1
    
    # 1. Add customer with spaces
    phone_raw = "089 948 1234"
    c1 = Customer(business_id=business_id, name="Test Customer", phone=phone_raw)
    repo.add(c1)
    await db_session.flush()
    
    # 2. Try to find by different format
    search_format = "0899481 234"
    
    # This should now work because we implemented normalization
    found_customer = await repo.get_by_phone(search_format, business_id)
    assert found_customer is not None, "Should find customer even with different phone format"
    assert found_customer.id == c1.id
    assert found_customer.phone == "0899481234", "Stored phone should be normalized"

    # 3. Test duplicate addition prevention (via logic in ToolExecutor or Service, but Repo just stores what it's given usually)
    # However, if we normalize on add, both should result in same generic string.
    
    # Let's test search with repo.search which also uses phone
    results = await repo.search(query=search_format, business_id=business_id)
    assert len(results) > 0
    assert results[0].id == c1.id

async def test_standardization_logic():
    # This will be the unit test for the function I will add
    from src.repositories import normalize_phone
    
    assert normalize_phone("089 948 1234") == "0899481234"
    assert normalize_phone("0899481 234") == "0899481234"
    assert normalize_phone("+49 89 123") == "+4989123"
    assert normalize_phone("123-456") == "123456"
