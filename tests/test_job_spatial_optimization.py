import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, Job, JobStatus
from src.repositories import JobRepository

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_job_spatial_optimization():
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
        )
        session.add(cust_dublin)
        await session.flush()

        # Job A: Explicit location in Cork (far from Dublin)
        # Cork: 51.8985, -8.4756
        job_cork = Job(
            description="Job in Cork",
            business_id=biz.id,
            customer_id=cust_dublin.id,
            latitude=51.8985,
            longitude=-8.4756,
            status=JobStatus.PENDING,
        )

        # Job B: No location, falls back to Customer (Dublin)
        job_dublin_implicit = Job(
            description="Job in Dublin (Implicit)",
            business_id=biz.id,
            customer_id=cust_dublin.id,
            latitude=None,
            longitude=None,
            status=JobStatus.PENDING,
        )

        session.add_all([job_cork, job_dublin_implicit])
        await session.commit()

        repo = JobRepository(session)

        # 1. Search near Dublin (Radius 20km)
        # Should find Job B (implicit), NOT Job A (Cork is > 200km away)
        results_dublin = await repo.search(
            query="all",
            business_id=biz.id,
            center_lat=53.3498,
            center_lon=-6.2603,
            radius=20000.0,
        )

        assert len(results_dublin) == 1
        assert results_dublin[0].id == job_dublin_implicit.id

        # 2. Search near Cork (Radius 20km)
        # Should find Job A, NOT Job B
        results_cork = await repo.search(
            query="all",
            business_id=biz.id,
            center_lat=51.8985,
            center_lon=-8.4756,
            radius=20000.0,
        )

        assert len(results_cork) == 1
        assert results_cork[0].id == job_cork.id

        # 3. Search halfway (Athlone) - Should find nothing
        # Athlone: 53.4239, -7.9407
        results_athlone = await repo.search(
            query="all",
            business_id=biz.id,
            center_lat=53.4239,
            center_lon=-7.9407,
            radius=20000.0,
        )

        assert len(results_athlone) == 0
