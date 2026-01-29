import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_credentials_db
from src.credentials_models import QuickBooksCredential
from src.repositories import BusinessRepository
from src.services.accounting.quickbooks_client import QuickBooksClient


class QuickBooksAuthService:
    def __init__(self, main_db: AsyncSession):
        self.main_db = main_db
        self.business_repo = BusinessRepository(main_db)
        self.qb_client = QuickBooksClient()

    def generate_auth_url(self, business_id: int) -> str:
        """
        Generates the authorization URL.
        State includes business_id and a random token.
        """
        csrf_token = f"{business_id}:{secrets.token_urlsafe(16)}"
        return self.qb_client.get_auth_url(csrf_token)

    async def handle_callback(self, auth_code: str, realm_id: str, state: str) -> dict:
        """
        Validates state and exchanges code for tokens.
        Returns token data.
        """
        if ":" not in state:
            raise ValueError("Invalid state format")

        business_id_str, _ = state.split(":", 1)
        try:
            business_id = int(business_id_str)
        except ValueError:
            raise ValueError("Invalid business ID in state")

        auth_client = self.qb_client.get_auth_client()
        auth_client.get_bearer_token(auth_code, realm_id=realm_id)

        token_data = {
            "business_id": business_id,
            "realm_id": realm_id,
            "access_token": auth_client.access_token,
            "refresh_token": auth_client.refresh_token,
            "expires_in": auth_client.expires_in,
            "x_refresh_token_expires_in": auth_client.x_refresh_token_expires_in,
        }

        # Save credentials and update business status
        await self.save_credentials(business_id, token_data)

        return token_data

    async def save_credentials(self, business_id: int, token_data: dict):
        """
        Upsert QuickBooksCredential in credentials_db and update Business in main_db.
        """
        # 1. Update Credentials DB (Synchronous)
        with get_credentials_db() as cred_db:
            cred = (
                cred_db.query(QuickBooksCredential)
                .filter_by(business_id=business_id)
                .first()
            )

            expiry_time = datetime.now(timezone.utc) + timedelta(
                seconds=token_data["expires_in"]
            )

            if not cred:
                # We need to use create_engine with pysqlcipher3 if possible, but here we just use the session
                cred = QuickBooksCredential(business_id=business_id)
                cred_db.add(cred)

            cred.realm_id = token_data["realm_id"]
            cred.access_token = token_data["access_token"]
            cred.refresh_token = token_data["refresh_token"]
            cred.token_expiry = expiry_time

            cred_db.commit()

        # 2. Update Business in Main DB (Asynchronous)
        business = await self.business_repo.get_by_id_global(business_id)
        if business:
            business.quickbooks_connected = True
            await self.main_db.commit()

    async def get_credentials(self, business_id: int) -> QuickBooksCredential:
        """Retrieve credentials from credentials_db."""
        with get_credentials_db() as cred_db:
            cred = (
                cred_db.query(QuickBooksCredential)
                .filter_by(business_id=business_id)
                .first()
            )
            return cred

    async def disconnect(self, business_id: int):
        """Delete credentials and update Business status."""
        # 1. Delete from Credentials DB
        with get_credentials_db() as cred_db:
            cred_db.query(QuickBooksCredential).filter_by(
                business_id=business_id
            ).delete()
            cred_db.commit()

        # 2. Update Business in Main DB
        business = await self.business_repo.get_by_id_global(business_id)
        if business:
            business.quickbooks_connected = False
            await self.main_db.commit()

    async def ensure_active_token(
        self, cred: QuickBooksCredential
    ) -> QuickBooksCredential:
        """
        Check if token is expiring and refresh if needed.
        Returns a valid credential.
        """
        if not cred:
            return None

        business_id = cred.business_id

        # Check if expiring in next 5 minutes
        now = datetime.now(timezone.utc)

        # Ensure cred.token_expiry is timezone-aware for comparison if it's not
        expiry = cred.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry < now + timedelta(minutes=5):
            # Refresh token
            auth_client = self.qb_client.get_auth_client(
                access_token=cred.access_token,
                refresh_token=cred.refresh_token,
            )
            auth_client.refresh()

            # Update DB
            token_data = {
                "business_id": business_id,
                "realm_id": cred.realm_id,
                "access_token": auth_client.access_token,
                "refresh_token": auth_client.refresh_token,
                "expires_in": auth_client.expires_in,
            }
            await self.save_credentials(business_id, token_data)

            # Return fresh credential
            return await self.get_credentials(business_id)

        return cred
