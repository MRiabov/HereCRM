import pytest
from unittest.mock import MagicMock, AsyncMock
from src.models import User, Business, UserRole
from src.api.dependencies.clerk_auth import verify_token
from src.services.auth_service import AuthService
from src.repositories import UserRepository
from sqlalchemy import select

@pytest.mark.asyncio
async def test_jit_create_user_phone_collision(async_session):
    # 1. Setup existing user with phone number
    existing_phone = "+15551234567"
    business = Business(name="Existing Biz")
    async_session.add(business)
    await async_session.flush()

    existing_user = User(
        name="Existing User",
        phone_number=existing_phone,
        email="existing@example.com",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(existing_user)
    await async_session.commit()

    # 2. Mock Clerk Client response
    mock_clerk_user = MagicMock()
    mock_clerk_user.first_name = "New"
    mock_clerk_user.last_name = "User"
    mock_clerk_user.username = "newuser"

    # Mock email addresses (different email to skip email matching)
    mock_email = MagicMock()
    mock_email.email_address = "new@example.com"
    mock_clerk_user.email_addresses = [mock_email]

    # Mock phone numbers (SAME phone number)
    mock_phone = MagicMock()
    mock_phone.phone_number = existing_phone
    mock_clerk_user.phone_numbers = [mock_phone]

    # Setup verify_token.clerk_client mock
    verify_token.clerk_client = MagicMock()
    verify_token.clerk_client.users.get.return_value = mock_clerk_user
    verify_token.clerk_client.users.update_metadata_async = AsyncMock()
    verify_token.clerk_client.organizations.get.return_value = MagicMock(name="New Org")

    # 3. Call _jit_create_user
    new_clerk_id = "clerk_new_123"

    # We expect this to SUCCEED and return the existing user with updated clerk_id
    user = await verify_token._jit_create_user(async_session, new_clerk_id, None)

    assert user.id == existing_user.id
    assert user.clerk_id == new_clerk_id
    assert user.phone_number == existing_phone
    # Email should NOT be updated because existing user has an email
    assert user.email == "existing@example.com"

@pytest.mark.asyncio
async def test_auth_service_sync_clerk_user_phone_collision(async_session):
    # 1. Setup existing user with phone number
    existing_phone = "+15559876543"
    business = Business(name="Existing Biz 2")
    async_session.add(business)
    await async_session.flush()

    existing_user = User(
        name="Existing User 2",
        phone_number=existing_phone,
        email="existing2@example.com",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    async_session.add(existing_user)
    await async_session.commit()

    # 2. Setup AuthService
    service = AuthService(async_session)
    service.clerk_client = MagicMock()
    service.clerk_client.users.update_metadata_async = AsyncMock()

    # 3. Call sync_clerk_user with same phone but different email
    data = {
        "id": "clerk_sync_123",
        "email_addresses": [{"email_address": "new2@example.com"}],
        "phone_numbers": [{"phone_number": existing_phone}],
        "first_name": "Sync",
        "last_name": "User"
    }

    # This should now SUCCEED and update the existing user
    await service.sync_clerk_user(data)

    # Verify updates
    await async_session.refresh(existing_user)
    assert existing_user.clerk_id == "clerk_sync_123"
    assert existing_user.email == "new2@example.com"

@pytest.mark.asyncio
async def test_get_or_create_user_no_creation(async_session):
    service = AuthService(async_session)
    phone = "+19999999999"

    # Call with create=False
    user, is_new = await service.get_or_create_user(phone, create=False)

    assert user is None
    assert is_new is False

    # Verify no user created in DB
    result = await async_session.execute(select(User).where(User.phone_number == phone))
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_get_or_create_user_creation(async_session):
    service = AuthService(async_session)
    phone = "+18888888888"

    # Call with create=True (default)
    user, is_new = await service.get_or_create_user(phone, create=True)

    assert user is not None
    assert is_new is True
    assert user.phone_number == phone

    # Verify user created in DB
    result = await async_session.execute(select(User).where(User.phone_number == phone))
    assert result.scalar_one_or_none() is not None
