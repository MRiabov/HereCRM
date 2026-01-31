from sqlalchemy.ext.asyncio import AsyncSession
import logging
from clerk_backend_api import Clerk
from src.config import settings
from src.models import User, Business, UserRole
from src.repositories import UserRepository, BusinessRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)
        self.clerk_client = Clerk(bearer_auth=settings.clerk_secret_key)

    async def get_or_create_user(self, phone: str) -> tuple[User, bool]:
        """
        Retrieves a user by phone number. If not found, creates a new Business
        and a new User (Owner) linked to that business.
        Returns a tuple of (User, is_new).
        """
        user = await self.user_repo.get_by_phone(phone)
        if user:
            return user, False

        # Create new Business and User
        business = Business(name=f"Business of {phone}")
        self.session.add(business)
        # Flush to generate ID for the business
        await self.session.flush()

        user = User(phone_number=phone, business_id=business.id, role=UserRole.OWNER)
        self.user_repo.add(user)
        # Flush to make the user available in the session identity map
        # and ensure IDs are generated if needed immediately
        await self.session.flush()

        return user, True

    async def get_or_create_user_by_identity(self, identity: str) -> tuple[User, bool]:
        """
        Identify user by email or phone.
        """
        if "@" in identity:
            user = await self.user_repo.get_by_email(identity)
            if user:
                return user, False

            # Create new Business and User by email
            business = Business(name=f"Business of {identity}")
            self.session.add(business)
            await self.session.flush()

            user = User(email=identity, business_id=business.id, role=UserRole.OWNER)
            self.user_repo.add(user)
            await self.session.flush()
            return user, True
        else:
            return await self.get_or_create_user(identity)

    async def sync_clerk_user(self, data: dict):
        """
        Syncs a user from Clerk webhook data.
        """
        clerk_id = data.get("id")
        if not clerk_id:
            return

        email_addresses = data.get("email_addresses", [])
        phone_numbers = data.get("phone_numbers", [])
        primary_email = (
            email_addresses[0].get("email_address") if email_addresses else None
        )
        primary_phone = phone_numbers[0].get("phone_number") if phone_numbers else None

        first_name = data.get("first_name") or ""
        last_name = data.get("last_name") or ""
        name = f"{first_name} {last_name}".strip() or "Unknown"

        user = await self.user_repo.get_by_clerk_id(clerk_id)
        if user:
            # Update existing user
            user.email = primary_email
            user.phone_number = primary_phone
            user.name = name
        else:
            # Create new user
            # First check if email already exists (orphaned account or re-creation)
            if primary_email:
                user = await self.user_repo.get_by_email(primary_email)
                if user:
                    user.clerk_id = clerk_id
                    user.name = name
                    user.phone_number = primary_phone
                    await self.session.flush()
                else:
                    # User model requires business_id (NOT NULL)
                    # Create a personal business for the user
                    business = Business(name=f"Business of {name}", clerk_org_id=None)
                    self.session.add(business)
                    await self.session.flush()

                    user = User(
                        clerk_id=clerk_id,
                        email=primary_email,
                        phone_number=primary_phone,
                        name=name,
                        business_id=business.id,
                        role=UserRole.OWNER,  # Default to owner of their personal business
                    )
                    self.user_repo.add(user)
            else:
                # Fallback for phone-only or no-email signups
                business = Business(name=f"Business of {name}", clerk_org_id=None)
                self.session.add(business)
                await self.session.flush()

                user = User(
                    clerk_id=clerk_id,
                    email=None,
                    phone_number=primary_phone,
                    name=name,
                    business_id=business.id,
                    role=UserRole.OWNER,
                )
                self.user_repo.add(user)

        await self.session.flush()

        # Update explicit Clerk Metadata
        if clerk_id and user:
            try:
                await self.clerk_client.users.update_metadata_async(
                    user_id=clerk_id,
                    public_metadata={
                        "business_id": user.business_id,
                        "role": user.role.value,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to sync metadata for Clerk user {clerk_id}: {e}")

    async def sync_clerk_org(self, data: dict):
        """
        Syncs an organization from Clerk webhook data.
        """
        clerk_org_id = data.get("id")
        if not clerk_org_id:
            return

        name = data.get("name")

        # Check if business exists
        business = await self.business_repo.get_by_clerk_id(clerk_org_id)

        if business:
            business.name = name
        else:
            business = Business(clerk_org_id=clerk_org_id, name=name)
            self.session.add(business)

        await self.session.flush()

    async def sync_clerk_membership(self, data: dict):
        """
        Syncs a user's membership in an organization.
        """
        user_clerk_id = data.get("public_user_data", {}).get("user_id")
        org_clerk_id = data.get("organization", {}).get("id")
        role_key = data.get("role", "")  # e.g. "org:admin"

        if not user_clerk_id or not org_clerk_id:
            return

        user = await self.user_repo.get_by_clerk_id(user_clerk_id)
        if not user:
            return

        # Resolve business
        business = await self.business_repo.get_by_clerk_id(org_clerk_id)

        if not business:
            # Maybe create? Or wait for org.created event.
            # For robustness, we could create.
            return

        user.business_id = business.id

        # Map roles
        if "admin" in role_key:
            user.role = UserRole.OWNER
        elif "MANAGER" in role_key:
            user.role = UserRole.MANAGER
        elif "member" in role_key:
            user.role = UserRole.EMPLOYEE

        await self.session.flush()

        # Update Clerk Metadata for membership sync
        try:
            await self.clerk_client.users.update_metadata_async(
                user_id=user_clerk_id,
                public_metadata={
                    "business_id": user.business_id,
                    "role": user.role.value,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to sync membership metadata for Clerk user {user_clerk_id}: {e}"
            )

    async def delete_clerk_user(self, data: dict):
        """
        Handles user.deleted event from Clerk.
        """
        clerk_id = data.get("id")
        if not clerk_id:
            return

        user = await self.user_repo.get_by_clerk_id(clerk_id)
        if not user:
            return

        # Cleanup dependent records that aren't on automatic CASCADE
        from src.models import ConversationState, WageConfiguration
        from sqlalchemy import delete

        await self.session.execute(
            delete(ConversationState).where(ConversationState.user_id == user.id)
        )
        await self.session.execute(
            delete(WageConfiguration).where(WageConfiguration.user_id == user.id)
        )

        # Delete user
        await self.user_repo.delete(user)
        await self.session.flush()
