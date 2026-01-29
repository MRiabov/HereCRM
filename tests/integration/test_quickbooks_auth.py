import os
import unittest.mock as mock
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.credentials_models import CredentialsBase, QuickBooksCredential
from src.models import Business
from src.services.accounting.quickbooks_auth import QuickBooksAuthService


@pytest.fixture
def mock_credentials_db():
    """Create a temporary in-memory database for credentials testing."""
    engine = create_engine("sqlite:///:memory:")
    CredentialsBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def auth_service(async_session, mock_credentials_db):
    """Create QuickBooksAuthService with mocked credentials DB."""
    env_vars = {
        "QB_CLIENT_ID": "test_client_id",
        "QB_CLIENT_SECRET": "test_client_secret",
        "QB_REDIRECT_URI": f"http://localhost:{os.getenv('BACKEND_PORT', '8000')}/callback",
    }
    with (
        mock.patch(
            "src.services.accounting.quickbooks_auth.get_credentials_db"
        ) as mock_get_db,
        mock.patch.dict(os.environ, env_vars),
    ):
        mock_get_db.return_value = mock_credentials_db
        service = QuickBooksAuthService(async_session)
        yield service


@pytest.mark.asyncio
async def test_generate_auth_url(auth_service):
    """Test generating the authorization URL."""
    business_id = 1
    url = auth_service.generate_auth_url(business_id)

    assert "client_id=" in url
    assert "response_type=code" in url
    assert "scope=com.intuit.quickbooks.accounting" in url
    assert f"state={business_id}%3A" in url


@pytest.mark.asyncio
async def test_handle_callback(auth_service, async_session, mock_credentials_db):
    """Test handling the OAuth callback."""
    # Setup business
    business = Business(id=1, name="Test Business")
    async_session.add(business)
    await async_session.commit()

    auth_code = "test_code"
    realm_id = "12345"
    state = "1:random_state"

    # Mock OAuth client
    with mock.patch(
        "src.services.accounting.quickbooks_client.AuthClient"
    ) as MockOAuth:
        mock_instance = MockOAuth.return_value
        mock_instance.access_token = "access_123"
        mock_instance.refresh_token = "refresh_456"
        mock_instance.expires_in = 3600
        mock_instance.x_refresh_token_expires_in = 8640000

        token_data = await auth_service.handle_callback(auth_code, realm_id, state)

        assert token_data["access_token"] == "access_123"
        assert token_data["realm_id"] == realm_id

        # Verify saved in credentials DB
        cred = (
            mock_credentials_db.query(QuickBooksCredential)
            .filter_by(business_id=1)
            .first()
        )
        assert cred is not None
        assert cred.access_token == "access_123"
        assert cred.realm_id == "12345"

        # Verify business updated in main DB
        await async_session.refresh(business)
        assert business.quickbooks_connected is True


@pytest.mark.asyncio
async def test_ensure_active_token_no_refresh(auth_service, mock_credentials_db):
    """Test token check when no refresh is needed."""
    # Create valid credential
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    cred = QuickBooksCredential(
        business_id=1,
        realm_id="12345",
        access_token="valid_access",
        refresh_token="valid_refresh",
        token_expiry=expiry,
    )
    mock_credentials_db.add(cred)
    mock_credentials_db.commit()

    # Call ensure_active_token
    result = await auth_service.ensure_active_token(cred)

    assert result.access_token == "valid_access"


@pytest.mark.asyncio
async def test_ensure_active_token_with_refresh(auth_service, mock_credentials_db):
    """Test token refresh when expiring soon."""
    # Create expiring credential (4 minutes from now)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=4)
    cred = QuickBooksCredential(
        business_id=1,
        realm_id="12345",
        access_token="old_access",
        refresh_token="old_refresh",
        token_expiry=expiry,
    )
    mock_credentials_db.add(cred)
    mock_credentials_db.commit()

    # Mock OAuth client refresh
    with mock.patch(
        "src.services.accounting.quickbooks_client.AuthClient"
    ) as MockOAuth:
        mock_instance = MockOAuth.return_value
        mock_instance.access_token = "new_access"
        mock_instance.refresh_token = "new_refresh"
        mock_instance.expires_in = 3600

        # Let's mock business_repo to avoid needing real business in main DB for this test
        auth_service.business_repo = mock.AsyncMock()

        result = await auth_service.ensure_active_token(cred)

        assert result.access_token == "new_access"
        assert result.refresh_token == "new_refresh"

        # Verify it was updated in mock_credentials_db
        updated_cred = (
            mock_credentials_db.query(QuickBooksCredential)
            .filter_by(business_id=1)
            .first()
        )
        assert updated_cred.access_token == "new_access"


@pytest.mark.asyncio
async def test_disconnect(auth_service, async_session, mock_credentials_db):
    """Test disconnecting QuickBooks."""
    # Setup business and credentials
    business = Business(id=1, name="Connected Business", quickbooks_connected=True)
    async_session.add(business)
    await async_session.commit()

    cred = QuickBooksCredential(
        business_id=1,
        realm_id="12345",
        access_token="access",
        refresh_token="refresh",
        token_expiry=datetime.now(timezone.utc),
    )
    mock_credentials_db.add(cred)
    mock_credentials_db.commit()

    # Disconnect
    await auth_service.disconnect(1)

    # Verify credentials deleted
    cred_after = (
        mock_credentials_db.query(QuickBooksCredential).filter_by(business_id=1).first()
    )
    assert cred_after is None

    # Verify business updated
    await async_session.refresh(business)
    assert business.quickbooks_connected is False
