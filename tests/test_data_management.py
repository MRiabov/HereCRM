import pytest
import pytest_asyncio
import pandas as pd
import os
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, Job, PipelineStage
from src.services.data_management import DataManagementService
from src.repositories import CustomerRepository, JobRepository

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session

    await engine.dispose()

@pytest_asyncio.fixture
async def setup_business(test_session):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.commit()
    return biz

@pytest.mark.asyncio
async def test_import_data_csv(test_session, setup_business, tmp_path):
    # 1. Prepare dummy CSV file
    data = {
        "name": ["John Doe", "Jane Smith"],
        "phone": ["1234567890", "0987654321"],
        "address": ["123 Main St", "456 High St"],
        "city": ["Dublin", "Cork"],
        "notes": ["Note 1", "Note 2"],
        "job_description": ["Clean windows", "Clean gutters"],
        "job_price": [100.0, 150.0],
        "job_status": ["PENDING", "COMPLETED"]
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "test_import.csv"
    df.to_csv(csv_path, index=False)

    service = DataManagementService(test_session)

    # 2. Run Import
    import_job = await service.import_data(
        business_id=setup_business.id,
        file_url=str(csv_path),
        media_type="text/csv"
    )

    assert import_job.status == "COMPLETED"
    assert import_job.record_count == 2

    # 3. Verify Data in DB
    cust_repo = CustomerRepository(test_session)
    cust1 = await cust_repo.get_by_phone("1234567890", setup_business.id)
    assert cust1 is not None
    assert cust1.name == "John Doe"
    assert cust1.city == "Dublin"

    job_repo = JobRepository(test_session)
    jobs1 = await job_repo.search("Clean windows", setup_business.id)
    assert len(jobs1) >= 1
    assert jobs1[0].customer_id == cust1.id
    assert jobs1[0].value == 100.0

@pytest.mark.asyncio
async def test_export_data_csv(test_session, setup_business):
    # 1. Seed Data
    cust = Customer(
        business_id=setup_business.id,
        name="Export Test",
        phone="5555555555",
        city="Dublin",
        pipeline_stage=PipelineStage.CONTACTED
    )
    test_session.add(cust)
    await test_session.flush()

    job = Job(
        business_id=setup_business.id,
        customer_id=cust.id,
        description="Test Job",
        value=200.0
    )
    test_session.add(job)
    await test_session.commit()

    service = DataManagementService(test_session)

    # 2. Run Export
    with patch("src.services.data_management.storage_service") as mock_storage:
        # Mock storage to return a local path so os.path.exists works in this test
        # (Though in reality it would be a URL)
        export_file = "test_export_output.csv"
        mock_storage.upload_file.return_value = export_file
        
        export_req = await service.export_data(
            business_id=setup_business.id,
            query="Dublin",
            format="csv"
        )

        assert export_req.status == "COMPLETED"
        assert export_req.public_url == export_file
        
        # Capture the content written to mock storage
        args, _ = mock_storage.upload_file.call_args
        file_bytes, _, _ = args
        with open(export_file, "wb") as f:
            f.write(file_bytes)

    # 3. Verify Content
    assert os.path.exists(export_file)
    df = pd.read_csv(export_file)
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Export Test"
    assert str(df.iloc[0]["phone"]) == "5555555555"

    # Cleanup
    os.remove(export_req.public_url)
