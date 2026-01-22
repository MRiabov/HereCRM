import pytest
import tempfile
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Business, Customer, Service, SyncLog, QuickBooksSyncStatus
from src.credentials_models import QuickBooksCredential, PYSQLCIPHER_AVAILABLE


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    os.unlink(path)


@pytest.fixture
def temp_credentials_db():
    """Create a temporary encrypted credentials database for testing."""
    if not PYSQLCIPHER_AVAILABLE:
        pytest.skip("pysqlcipher3 not available - skipping credentials database tests")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name
    
    # Set test environment variable
    original_key = os.getenv("CREDENTIALS_DB_KEY")
    test_key = "test_encryption_key_12345"
    os.environ["CREDENTIALS_DB_KEY"] = test_key
    
    try:
        from src.credentials_models import CredentialsBase
        # Use the temp path for testing
        from sqlalchemy import create_engine
        from sqlalchemy.pool import StaticPool
        
        test_engine = create_engine(
            f"sqlite+pysqlcipher://:{test_key}@/{temp_path}?cipher=aes-256-cfb&kdf_iter=64000",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        CredentialsBase.metadata.create_all(test_engine)
        SessionLocal = sessionmaker(bind=test_engine)
        session = SessionLocal()
        yield session
        session.close()
        
    finally:
        # Restore original environment
        if original_key:
            os.environ["CREDENTIALS_DB_KEY"] = original_key
        else:
            os.environ.pop("CREDENTIALS_DB_KEY", None)
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass


class TestMainDatabaseModels:
    """Test models in the main database."""
    
    def test_business_creation(self, temp_db):
        """Test Business model creation and QuickBooks fields."""
        business = Business(
            name="Test Business",
            quickbooks_connected=False,
            quickbooks_last_sync=None
        )
        temp_db.add(business)
        temp_db.commit()
        temp_db.refresh(business)
        
        assert business.id is not None
        assert business.name == "Test Business"
        assert business.quickbooks_connected is False
        assert business.quickbooks_last_sync is None
        
        # Test QuickBooks connection update
        business.quickbooks_connected = True
        business.quickbooks_last_sync = datetime.now(timezone.utc)
        temp_db.commit()
        temp_db.refresh(business)
        
        assert business.quickbooks_connected is True
        assert business.quickbooks_last_sync is not None
    
    def test_customer_quickbooks_fields(self, temp_db):
        """Test Customer QuickBooks sync fields."""
        business = Business(name="Test Business")
        temp_db.add(business)
        temp_db.commit()
        
        customer = Customer(
            business_id=business.id,
            name="Test Customer",
            quickbooks_id=None,
            quickbooks_sync_status=QuickBooksSyncStatus.PENDING,
            quickbooks_sync_error=None
        )
        temp_db.add(customer)
        temp_db.commit()
        temp_db.refresh(customer)
        
        assert customer.id is not None
        assert customer.quickbooks_sync_status == QuickBooksSyncStatus.PENDING
        assert customer.quickbooks_id is None
        assert customer.quickbooks_sync_error is None
        
        # Test sync status update
        customer.quickbooks_id = "qb_12345"
        customer.quickbooks_sync_status = QuickBooksSyncStatus.SYNCED
        customer.quickbooks_synced_at = datetime.now(timezone.utc)
        temp_db.commit()
        temp_db.refresh(customer)
        
        assert customer.quickbooks_id == "qb_12345"
        assert customer.quickbooks_sync_status == QuickBooksSyncStatus.SYNCED
        assert customer.quickbooks_synced_at is not None
    
    def test_service_quickbooks_fields(self, temp_db):
        """Test Service QuickBooks sync fields."""
        business = Business(name="Test Business")
        temp_db.add(business)
        temp_db.commit()
        
        service = Service(
            business_id=business.id,
            name="Test Service",
            default_price=100.0,
            quickbooks_sync_status=QuickBooksSyncStatus.PENDING
        )
        temp_db.add(service)
        temp_db.commit()
        temp_db.refresh(service)
        
        assert service.id is not None
        assert service.quickbooks_sync_status == QuickBooksSyncStatus.PENDING
        
        # Test failed sync
        service.quickbooks_sync_status = QuickBooksSyncStatus.FAILED
        service.quickbooks_sync_error = "API Error: Invalid data"
        temp_db.commit()
        temp_db.refresh(service)
        
        assert service.quickbooks_sync_status == QuickBooksSyncStatus.FAILED
        assert service.quickbooks_sync_error == "API Error: Invalid data"
    
    def test_sync_log_creation(self, temp_db):
        """Test SyncLog model creation."""
        business = Business(name="Test Business")
        temp_db.add(business)
        temp_db.commit()
        
        sync_log = SyncLog(
            business_id=business.id,
            sync_type="manual",
            records_processed=10,
            records_succeeded=8,
            records_failed=2,
            status="partial_success",
            error_details={"failed_records": [3, 7]},
            duration_seconds=45.5
        )
        temp_db.add(sync_log)
        temp_db.commit()
        temp_db.refresh(sync_log)
        
        assert sync_log.id is not None
        assert sync_log.business_id == business.id
        assert sync_log.sync_type == "manual"
        assert sync_log.records_processed == 10
        assert sync_log.records_succeeded == 8
        assert sync_log.records_failed == 2
        assert sync_log.status == "partial_success"
        assert sync_log.error_details == {"failed_records": [3, 7]}
        assert sync_log.duration_seconds == 45.5
        assert sync_log.sync_timestamp is not None
    
    def test_business_sync_logs_relationship(self, temp_db):
        """Test relationship between Business and SyncLog."""
        business = Business(name="Test Business")
        temp_db.add(business)
        temp_db.commit()
        
        # Create multiple sync logs
        for i in range(3):
            sync_log = SyncLog(
                business_id=business.id,
                sync_type="scheduled",
                records_processed=5,
                records_succeeded=5,
                records_failed=0,
                status="success"
            )
            temp_db.add(sync_log)
        
        temp_db.commit()
        temp_db.refresh(business)
        
        assert len(business.sync_logs) == 3
        for log in business.sync_logs:
            assert log.business_id == business.id


class TestCredentialsDatabase:
    """Test models in the encrypted credentials database."""
    
    def test_quickbooks_credential_creation(self, temp_credentials_db):
        """Test QuickBooksCredential model creation."""
        credential = QuickBooksCredential(
            business_id=1,
            realm_id="realm_12345",
            access_token="access_token_abc",
            refresh_token="refresh_token_xyz",
            token_expiry=datetime.now(timezone.utc)
        )
        temp_credentials_db.add(credential)
        temp_credentials_db.commit()
        temp_credentials_db.refresh(credential)
        
        assert credential.business_id == 1
        assert credential.realm_id == "realm_12345"
        assert credential.access_token == "access_token_abc"
        assert credential.refresh_token == "refresh_token_xyz"
        assert credential.token_expiry is not None
        assert credential.connected_at is not None
        assert credential.updated_at is not None
    
    def test_credential_encryption(self, temp_credentials_db):
        """Test that credentials are stored in encrypted database."""
        credential = QuickBooksCredential(
            business_id=2,
            realm_id="realm_67890",
            access_token="sensitive_access_token",
            refresh_token="sensitive_refresh_token",
            token_expiry=datetime.now(timezone.utc)
        )
        temp_credentials_db.add(credential)
        temp_credentials_db.commit()
        
        # Verify we can retrieve it
        retrieved = temp_credentials_db.query(QuickBooksCredential).filter_by(
            business_id=2
        ).first()
        
        assert retrieved is not None
        assert retrieved.access_token == "sensitive_access_token"
        assert retrieved.refresh_token == "sensitive_refresh_token"


class TestDatabaseConnection:
    """Test database connections and setup."""
    
    def test_credentials_db_file_creation(self):
        """Test that credentials database setup handles missing dependencies gracefully."""
        # This test verifies the database setup in credentials_models.py
        from src.credentials_models import credentials_engine, PYSQLCIPHER_AVAILABLE
        
        if PYSQLCIPHER_AVAILABLE:
            # The database should be created at module import time
            # We can verify by checking if the engine exists
            assert credentials_engine is not None
            
            # Check that tables are created
            inspector = credentials_engine.dialect.get_columns(credentials_engine, "quickbooks_credentials")
            assert len(inspector) > 0  # Should have columns
        else:
            # Should gracefully handle missing pysqlcipher3
            assert credentials_engine is None


if __name__ == "__main__":
    pytest.main([__file__])
