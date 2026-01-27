
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.data_management import DataManagementService
from src.models import Business, Customer, PipelineStage
from datetime import datetime

@pytest.mark.asyncio
async def test_export_empty_query(async_session: AsyncSession):
    # Setup
    business = Business(name="Test Biz Empty")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    # NO data seeded

    service = DataManagementService(async_session)
    
    with patch("src.services.data_management.storage_service") as mock_storage:
        mock_storage.upload_file.return_value = "https://s3.fake/export.csv"
        
        # Action: Export with empty query
        result = await service.export_data(business.id, query="", format="csv")
        
        # Verify
        assert result.status == "completed"
        assert result.public_url == "https://s3.fake/export.csv"
        
        # Verify call args
        args, _ = mock_storage.upload_file.call_args
        file_bytes, key, content_type = args
        content = file_bytes.decode('utf-8')
        
        # Should contain headers at least?
        assert "id,name,phone,address,notes,stage,created_at" in content

@pytest.mark.asyncio
async def test_export_none_query(async_session: AsyncSession):
    # Setup
    business = Business(name="Test Biz None")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    service = DataManagementService(async_session)
    
    with patch("src.services.data_management.storage_service") as mock_storage:
        mock_storage.upload_file.return_value = "https://s3.fake/export.csv"
        
        # Action: Export with None query (passed as query=None)
        # trigger_export in data_management.py handles query=payload.query or ""
        # but let's test service directly with None if possible
        result = await service.export_data(business.id, query=None, format="csv")
        
        assert result.status == "completed"

@pytest.mark.asyncio
async def test_export_excel_empty(async_session: AsyncSession):
    business = Business(name="Test Biz Excel Empty")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    service = DataManagementService(async_session)
    
    with patch("src.services.data_management.storage_service") as mock_storage:
        mock_storage.upload_file.return_value = "https://s3.fake/export.xlsx"
        
        # Action: Export Excel with no data
        result = await service.export_data(business.id, query="", format="excel")
        
        assert result.status == "completed"
