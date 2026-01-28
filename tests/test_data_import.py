import pytest
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.services.data_management import DataManagementService
from src.models import Business, Customer, Job, ImportJob, ExportStatus, JobStatus

@pytest.fixture
def mock_file_content():
    data = """Name,Phone,Address,Notes,Job Description,Job Price
John Doe,555-0101,123 Main St,Friendly guy,Fix sink,150.00
Jane Smith,555-0102,456 Oak Ave,Bad payer,Paint wall,200.00
    """
    return data.encode('utf-8')

@pytest.mark.asyncio
async def test_import_happy_path(async_session: AsyncSession):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    service = DataManagementService(async_session)
    
    # Create a dummy CSV file on disk
    import os
    filename = "test_import.csv"
    with open(filename, "w") as f:
        f.write("Name,Phone,Address,Notes,Job Description,Job Price\n")
        f.write("John Doe,555-0101,123 Main St,Friendly guy,Fix sink,150.00\n")
        f.write("Jane Smith,555-0102,456 Oak Ave,Bad payer,Paint wall,200.00\n")

    try:
        # Run Import
        job = await service.import_data(business.id, filename, "text/csv")
        
        assert job.status == ExportStatus.COMPLETED
        assert job.record_count == 2
        
        # Verify Customers
        result = await async_session.execute(select(Customer).where(Customer.business_id == business.id))
        customers = result.scalars().all()
        assert len(customers) == 2
        
        john = next(c for c in customers if c.name == "John Doe")
        assert john.phone == "5550101"
        assert john.street == "123 Main St"
        
        # Verify Jobs
        result = await async_session.execute(select(Job).where(Job.business_id == business.id))
        jobs = result.scalars().all()
        assert len(jobs) == 2
        
        sink_job = next(j for j in jobs if j.description == "Fix sink")
        assert sink_job.value == 150.00
        assert sink_job.customer_id == john.id

    finally:
        if os.path.exists(filename):
            os.remove(filename)

@pytest.mark.asyncio
async def test_import_atomicity_failure(async_session: AsyncSession):
    """
    Test that if one row fails or an error occurs during processing, 
    NO customers/jobs are committed, but the ImportJob is saved as 'FAILED'.
    """
    business = Business(name="Test Biz Atom")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    service = DataManagementService(async_session)

    # We'll inject a failure by mocking _process_dataframe or by providing data that causes a DB error
    # But since _process_dataframe catches nothing, we can just patch it to raise an Exception
    # OR we can pass bad data if we had stricter validation. 
    # Let's simple create a file, and MOCK _process_dataframe to raise.
    
    filename = "test_fail.csv"
    with open(filename, "w") as f:
        f.write("Name\nJohn\n")
        
    # Monkey patch _process_dataframe on this instance
    original_process = service._process_dataframe
    
    async def mock_process(bid, df):
        # Do one successful insert then raise
        cust = Customer(business_id=bid, name="Should Rollback", phone="000")
        async_session.add(cust)
        await async_session.flush() 
        raise ValueError("Simulated Failure")

    service._process_dataframe = mock_process

    try:
        job = await service.import_data(business.id, filename, "text/csv")
        
        assert job.status == ExportStatus.FAILED
        assert "Simulated Failure" in job.error_log[0]['error']
        
        # Verify Rollback - Customer "Should Rollback" should NOT exist
        result = await async_session.execute(select(Customer).where(Customer.phone == "000"))
        assert result.scalars().first() is None
        
        # Verify Block - ImportJob MUST exist
        result = await async_session.execute(select(ImportJob).where(ImportJob.id == job.id))
        saved_job = result.scalars().first()
        assert saved_job is not None
        assert saved_job.status == ExportStatus.FAILED

    finally:
        if os.path.exists(filename):
            os.remove(filename)
            
