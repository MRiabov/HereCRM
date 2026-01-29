import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer
from src.repositories import CustomerRepository

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_customer_spatial_optimization():
    # Setup DB
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with SessionLocal() as session:
        # Create Business
        biz = Business(name="Spatial Biz")
        session.add(biz)
        await session.flush()

        # Customer in Dublin
        cust_dublin = Customer(
            name="Dublin Customer",
            business_id=biz.id,
            latitude=53.3498,
            longitude=-6.2603,
            phone="123",
        )

        # Customer in Cork (far from Dublin)
        # Cork: 51.8985, -8.4756
        cust_cork = Customer(
            name="Cork Customer",
            business_id=biz.id,
            latitude=51.8985,
            longitude=-8.4756,
            phone="456",
        )

        # Customer just outside 10km radius from Dublin
        # 1 degree lat is approx 111km. 0.1 degree is 11km.
        # Dublin + 0.15 deg lat should be outside 10km
        cust_far_dublin = Customer(
            name="Far Dublin Customer",
            business_id=biz.id,
            latitude=53.3498 + 0.15,
            longitude=-6.2603,
            phone="789",
        )

        session.add_all([cust_dublin, cust_cork, cust_far_dublin])
        await session.commit()

        repo = CustomerRepository(session)

        # 1. Search near Dublin (Radius 10km)
        # Should find only cust_dublin
        results_dublin = await repo.search(
            query="all",
            business_id=biz.id,
            center_lat=53.3498,
            center_lon=-6.2603,
            radius=10000.0,
        )

        assert len(results_dublin) == 1
        assert results_dublin[0].id == cust_dublin.id

        # 2. Search near Cork (Radius 20km)
        # Should find only cust_cork
        results_cork = await repo.search(
            query="all",
            business_id=biz.id,
            center_lat=51.8985,
            center_lon=-8.4756,
            radius=20000.0,
        )

        assert len(results_cork) == 1
        assert results_cork[0].id == cust_cork.id

        # 3. Search with larger radius (200km) near Dublin
        # Should find Dublin and Far Dublin, and maybe Cork?
        # Dublin to Cork is ~219km air distance.
        # Let's check radius 300km
        results_large = await repo.search(
            query="all",
            business_id=biz.id,
            center_lat=53.3498,
            center_lon=-6.2603,
            radius=300000.0,
        )

        # Should find all 3
        ids = [c.id for c in results_large]
        assert cust_dublin.id in ids
        assert cust_cork.id in ids
        assert cust_far_dublin.id in ids

        # 4. Dateline Crossing Test
        # Point A: 0, 179
        # Point B: 0, -179
        # Distance approx 222km
        cust_east = Customer(
            name="East", business_id=biz.id, latitude=0, longitude=179, phone="111"
        )
        cust_west = Customer(
            name="West", business_id=biz.id, latitude=0, longitude=-179, phone="222"
        )
        session.add_all([cust_east, cust_west])
        await session.commit()

        # Search at 0, 179 with radius 500km -> Should find West
        results_dateline = await repo.search(
            query="all",
            business_id=biz.id,
            center_lat=0,
            center_lon=179,
            radius=500000.0,
        )

        ids_dateline = [c.id for c in results_dateline]
        assert cust_east.id in ids_dateline
        assert cust_west.id in ids_dateline
