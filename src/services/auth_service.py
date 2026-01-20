from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Business
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

        user = User(phone_number=phone, business_id=business.id, role="owner")
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
            
            user = User(email=identity, business_id=business.id, role="owner")
            self.user_repo.add(user)
            await self.session.flush()
            return user, True
        else:
            return await self.get_or_create_user(identity)

