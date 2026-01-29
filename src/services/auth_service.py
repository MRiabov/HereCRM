from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Business, UserRole
from src.repositories import UserRepository, BusinessRepository


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)

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

        await self.session.flush()

    async def sync_clerk_org(self, data: dict):
        """
        Syncs an organization from Clerk webhook data.
        """
        clerk_org_id = data.get("id")
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
