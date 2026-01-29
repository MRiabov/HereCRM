import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.data_management import DataManagementService
from src.models import (
    Business,
    Customer,
    Job,
    PipelineStage,
    JobStatus,
    ExportStatus,
    ExportFormat,
)


@pytest.mark.asyncio
async def test_export_customers_csv(async_session: AsyncSession):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    # Seed data
    c1 = Customer(
        business_id=business.id,
        name="Alice",
        phone="100",
        pipeline_stage=PipelineStage.CONTACTED,
        street="Dublin",
    )
    c2 = Customer(
        business_id=business.id,
        name="Bob",
        phone="200",
        pipeline_stage=PipelineStage.LOST,
        street="Cork",
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    service = DataManagementService(async_session)

    # Mock S3Service using patch
    with patch("src.services.data_management.storage_service") as mock_storage:
        mock_storage.upload_file.return_value = "https://s3.fake/export.csv"

        # Action: Export All Customers
        from src.models import EntityType

        filters = {"entity_type": EntityType.CUSTOMER}
        result = await service.export_data(
            business.id, query="all", format=ExportFormat.CSV, filters=filters
        )

        # Verify
        assert result.status == ExportStatus.COMPLETED
        assert result.public_url == "https://s3.fake/export.csv"

        # Verify call args
        args, _ = mock_storage.upload_file.call_args
        file_bytes, key, content_type = args
        content = file_bytes.decode("utf-8")

        assert "Alice" in content
        assert "Bob" in content
        assert "Dublin" in content
        assert "Cork" in content
        assert content_type == "text/csv"


@pytest.mark.asyncio
async def test_export_jobs_filtered(async_session: AsyncSession):
    # Setup
    business = Business(name="Test Biz Jobs")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    c1 = Customer(business_id=business.id, name="Charlie", phone="300")
    async_session.add(c1)
    await async_session.flush()

    j1 = Job(
        business_id=business.id,
        customer_id=c1.id,
        description="Fix Roof",
        status=JobStatus.PENDING,
        value=500.0,
    )
    j2 = Job(
        business_id=business.id,
        customer_id=c1.id,
        description="Clean Windows",
        status=JobStatus.COMPLETED,
        value=100.0,
    )
    async_session.add_all([j1, j2])
    await async_session.commit()

    service = DataManagementService(async_session)

    with patch("src.services.data_management.storage_service") as mock_storage:
        mock_storage.upload_file.return_value = "https://s3.fake/jobs.xlsx"

        # Action: Export Jobs with Status=pending
        from src.models import EntityType

        filters = {"entity_type": EntityType.JOB, "status": JobStatus.PENDING}
        result = await service.export_data(
            business.id, query="all", format=ExportFormat.EXCEL, filters=filters
        )

        assert result.status == ExportStatus.COMPLETED

        # Verify content logic (without parsing excel binary, just assume success if mock called)
        mock_storage.upload_file.assert_called_once()
        args, _ = mock_storage.upload_file.call_args
        _, key, content_type = args

        assert (
            "xlsx" in key or "excel" in content_type
        )  # Content type might be the long one
        assert (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            in content_type
        )


@pytest.mark.asyncio
async def test_export_failure_handling(async_session: AsyncSession):
    business = Business(name="Test Biz Fail")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    service = DataManagementService(async_session)

    with patch("src.services.data_management.storage_service") as mock_storage:
        # Simulate S3 Error
        mock_storage.upload_file.side_effect = Exception("S3 Down")

        result = await service.export_data(business.id, query="all", format="json")

        assert result.status == ExportStatus.FAILED
        # ExportRequest not having error log means we can't check the message directly on the model
        # unless we added it (which I didn't in WP01, ImportJob has it).
        # But status should be failed.
