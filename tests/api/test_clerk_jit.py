import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import select
from src.models import User, Business, UserRole
from src.api.dependencies.clerk_auth import VerifyToken
from src.database import get_db
import os

# Set dummy env vars to avoid validation errors during import
os.environ["CLERK_JWKS_URL"] = "https://example.com/.well-known/jwks.json"
os.environ["CLERK_SECRET_KEY"] = "sk_test_123"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

@pytest.mark.asyncio
async def test_jit_create_user_phone_conflict(async_session):
    # 1. Create an existing user with a phone number (simulating WhatsApp user)
    # This user has NO clerk_id yet.
    business = Business(name="Existing Business")
    async_session.add(business)
    await async_session.flush()

    existing_phone = "+15551234567"
    existing_user = User(
        phone_number=existing_phone,
        business_id=business.id,
        role=UserRole.OWNER,
        email=None, # No email
        name="WhatsApp User"
    )
    async_session.add(existing_user)
    await async_session.commit()

    # 2. Setup VerifyToken with mocked Clerk client
    with patch("src.api.dependencies.clerk_auth.Clerk") as MockClerk:
        # Mock the Clerk instance
        mock_clerk_instance = MockClerk.return_value

        # Mock user data from Clerk
        clerk_user_id = "user_new_123"
        clerk_org_id = "org_new_123"

        mock_clerk_user = MagicMock()
        mock_clerk_user.id = clerk_user_id
        mock_clerk_user.first_name = "New"
        mock_clerk_user.last_name = "User"
        mock_clerk_user.username = "newuser"
        mock_clerk_user.email_addresses = [] # No email in Clerk either, or different one

        # Mock phone number in Clerk matching existing user
        mock_phone = MagicMock()
        mock_phone.phone_number = existing_phone
        mock_clerk_user.phone_numbers = [mock_phone]

        mock_clerk_instance.users.get.return_value = mock_clerk_user

        # Mock Organization data
        mock_org = MagicMock()
        mock_org.name = "New Org"
        mock_clerk_instance.organizations.get.return_value = mock_org

        # Instantiate VerifyToken
        # We need to ensure settings are patched if not picked up from env
        with patch("src.api.dependencies.clerk_auth.settings") as mock_settings:
            mock_settings.clerk_jwks_url = "https://example.com/.well-known/jwks.json"
            mock_settings.clerk_secret_key = "sk_test_123"

            verifier = VerifyToken()
            # Replace the clerk_client with our mock because __init__ created a new one
            verifier.clerk_client = mock_clerk_instance

            # 3. Call _jit_create_user
            user = await verifier._jit_create_user(async_session, clerk_user_id, clerk_org_id)

            # If we get here without error, check if it's the same user or a duplicate (which is impossible with unique constraint)
            assert user.id == existing_user.id, "Should have linked to existing user"
            assert user.clerk_id == clerk_user_id, "Should have updated clerk_id"
