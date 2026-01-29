import pytest
import os
import sqlite3
from unittest.mock import patch, MagicMock
from src.services.data_management import DataManagementService
from src.models import Business
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base

@pytest.mark.asyncio
async def test_backup_db_success(tmp_path):
    # Use a real file-based database for the backup test
    db_file = tmp_path / "test_crm.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    
    # Initialize the test DB
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)
    async with SessionLocal() as session:
        # Add some data
        biz = Business(name="Backup Test Business")
        session.add(biz)
        await session.commit()
        
        service = DataManagementService(session)
        
        # Patch DATABASE_URL and storage_service
        with patch("src.services.data_management.storage_service") as mock_storage, \
             patch("src.database.DATABASE_URL", db_url):
            
            mock_storage.upload_file.return_value = "http://s3/backup.sqlite"
            
            backup_url = await service.backup_db()
            
            assert backup_url == "http://s3/backup.sqlite"
            assert mock_storage.upload_file.called
            
            # Verify the uploaded content is a valid SQLite DB
            args, _ = mock_storage.upload_file.call_args
            file_bytes, s3_key, content_type = args
            
            assert content_type == "application/x-sqlite3"
            assert s3_key.startswith("backups/crm_db_")
            
            # Write bytes to a temp file and check with sqlite3
            test_backup = tmp_path / "test_backup.sqlite"
            with open(test_backup, "wb") as f:
                f.write(file_bytes)
                
            conn = sqlite3.connect(str(test_backup))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM businesses WHERE name='Backup Test Business'")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "Backup Test Business"
            conn.close()

    await engine.dispose()

@pytest.mark.asyncio
async def test_backup_endpoint_unauthorized(tmp_path):
    from fastapi.testclient import TestClient
    from src.main import app
    
    # Patch CRON_SECRET to ensure we know what to expect
    with patch.dict(os.environ, {"CRON_SECRET": "secret123"}):
        client = TestClient(app)
        # No secret header
        response = client.post("/api/v1/pwa/backup/trigger")
        assert response.status_code == 401
        
        # Wrong secret header
        response = client.post("/api/v1/pwa/backup/trigger", headers={"X-Cron-Secret": "wrong"})
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_backup_endpoint_success(tmp_path):
    from fastapi.testclient import TestClient
    from src.main import app
    
    # We need to mock the service call to avoid real DB/S3 interaction in the API test
    with patch.dict(os.environ, {"CRON_SECRET": "secret123"}), \
         patch("src.services.data_management.DataManagementService.backup_db") as mock_backup:
        
        mock_backup.return_value = "http://s3/backup.sqlite"
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/pwa/backup/trigger", 
            headers={"X-Cron-Secret": "secret123"}
        )
        
        assert response.status_code == 200
        assert response.json()["backup_url"] == "http://s3/backup.sqlite"
        assert response.json()["status"] == "success"
