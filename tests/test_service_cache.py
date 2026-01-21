import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models import Base, Service, Business
from src.repositories import ServiceRepository
from src.services.cache import ServiceCatalogCache

@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield SessionLocal
    await engine.dispose()

@pytest.mark.asyncio
async def test_service_cache(session_factory):
    business_id = 999

    # Clear cache before test
    ServiceCatalogCache.get_instance().clear()

    # 1. Setup
    async with session_factory() as session:
        session.add(Business(id=business_id, name="Cache Test Biz"))
        session.add(Service(business_id=business_id, name="Service 1", default_price=10.0))
        await session.commit()

    # 2. First fetch (Cache Miss)
    async with session_factory() as session:
        repo = ServiceRepository(session)
        services = await repo.get_all_for_business(business_id)
        assert len(services) == 1
        assert services[0].name == "Service 1"

        # Verify cache is populated
        cache = ServiceCatalogCache.get_instance()
        cached = cache.get(business_id)
        assert cached is not None
        assert len(cached) == 1
        assert cached[0]['name'] == "Service 1"
        version_before = cache.get_version(business_id)

    # 3. Second fetch (Cache Hit)
    async with session_factory() as session:
        repo = ServiceRepository(session)
        services = await repo.get_all_for_business(business_id)
        assert len(services) == 1
        # If it came from cache, it is not attached to this session
        from sqlalchemy import inspect
        ins = inspect(services[0])
        # It's a newly created instance so it looks transient
        assert ins.transient

    # 4. Invalidation on Add
    async with session_factory() as session:
        session.add(Service(business_id=business_id, name="Service 2", default_price=20.0))
        await session.commit()

        # Event listener should have cleared cache OR updated version
        cache = ServiceCatalogCache.get_instance()
        version_after = cache.get_version(business_id)
        assert version_after > version_before, "Cache version should increment on invalidation"

        # We don't strictly assert cache is None, because implicit reads might repopulate it.
        # But if it is populated, it MUST contain the new service.
        cached = cache.get(business_id)
        if cached is not None:
            assert len(cached) == 2
            names = [s['name'] for s in cached]
            assert "Service 2" in names

    # 5. Fetch again (Cache Miss -> Populate OR Cache Hit if repopulated)
    async with session_factory() as session:
        repo = ServiceRepository(session)
        services = await repo.get_all_for_business(business_id)
        assert len(services) == 2

    # 6. Invalidation on Update
    async with session_factory() as session:
        repo = ServiceRepository(session)
        s = await repo.get_by_name("Service 1", business_id)
        # Since get_by_name might return a transient object from cache, we must merge it to update
        s = await session.merge(s)
        s.default_price = 15.0
        version_before = cache.get_version(business_id)
        await session.commit()

        version_after = cache.get_version(business_id)
        assert version_after > version_before

    # 7. Check update reflected
    async with session_factory() as session:
        repo = ServiceRepository(session)
        services = await repo.get_all_for_business(business_id)
        s1 = next(s for s in services if s.name == "Service 1")
        assert s1.default_price == 15.0

    # 8. Invalidation on Delete
    async with session_factory() as session:
        repo = ServiceRepository(session)
        s = await repo.get_by_name("Service 2", business_id)
        # Merge before delete
        s = await session.merge(s)
        version_before = cache.get_version(business_id)
        await session.delete(s)
        await session.commit()

        version_after = cache.get_version(business_id)
        assert version_after > version_before

    # 9. Verify Delete
    async with session_factory() as session:
        repo = ServiceRepository(session)
        services = await repo.get_all_for_business(business_id)
        assert len(services) == 1
        assert services[0].name == "Service 1"

    # 10. Verify Merge & Update from Cache
    # Repopulate cache first
    async with session_factory() as session:
        repo = ServiceRepository(session)
        await repo.get_all_for_business(business_id)

    # Now simulate ToolExecutor behavior
    async with session_factory() as session:
        repo = ServiceRepository(session)
        services = await repo.get_all_for_business(business_id)
        svc = services[0]

        # Merge and Update
        merged_svc = await session.merge(svc)
        merged_svc.name = "Updated Service"
        await session.commit()

        # Verify update persisted
        updated = await repo.get_by_id(svc.id, business_id)
        assert updated.name == "Updated Service"
