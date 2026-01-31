import pytest
import io
import pandas as pd
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.data_management import DataManagementService
from src.models import (
    Business,
    Customer,
    Job,
    ExportStatus,
    ExportFormat,
    EntityType,
    PipelineStage,
    JobStatus,
)


@pytest.mark.asyncio
async def test_export_all_multi_sheet_excel(async_session: AsyncSession):
    # Setup
    business = Business(name="Multi Sheet Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    # Seed data: Customer and Job
    c1 = Customer(
        business_id=business.id,
        name="Alice Excel",
        phone="123456789",
        pipeline_stage=PipelineStage.CONTACTED,
    )
    async_session.add(c1)
    await async_session.flush()

    j1 = Job(
        business_id=business.id,
        customer_id=c1.id,
        description="Excel Job",
        status=JobStatus.PENDING,
        value=500.0,
    )
    async_session.add(j1)
    await async_session.commit()

    service = DataManagementService(async_session)

    with patch("src.services.data_management.storage_service") as mock_storage:
        mock_storage.upload_file.return_value = (
            "https://s3.fake/multi_sheet_export.xlsx"
        )

        # Action: Export EVERYTHING as EXCEL
        result = await service.export_data(
            business_id=business.id, query="all", format=ExportFormat.EXCEL
        )

        # Verify status
        assert result.status == ExportStatus.COMPLETED
        assert result.format == ExportFormat.EXCEL

        # Verify S3 upload
        mock_storage.upload_file.assert_called_once()
        args, _ = mock_storage.upload_file.call_args
        file_bytes, key, content_type = args

        assert (
            content_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert key.endswith(".xlsx")

        # Verify sheets
        excel_data = io.BytesIO(file_bytes)

        # This will read all sheets into a dict of DataFrames
        xl = pd.read_excel(excel_data, sheet_name=None)

        # Check if sheets "customers" and "jobs" are present
        assert "customers" in xl
        assert "jobs" in xl

        # Check content of sheets
        customers_df = xl["customers"]
        jobs_df = xl["jobs"]

        assert any(customers_df["name"] == "Alice Excel")
        assert any(jobs_df["description"] == "Excel Job")
