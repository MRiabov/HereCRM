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

    async def create_user_by_email(self, email: str) -> User:
        """
        Creates a new Business and User with the given email address.
        Returns the created User.
        """
        # Create new Business and User
        business = Business(name=f"Business of {email}")
        self.session.add(business)
        # Flush to generate ID for the business
        await self.session.flush()

        user = User(email=email, business_id=business.id, role="owner")
        self.user_repo.add(user)
        # Flush to make the user available in the session identity map
        await self.session.flush()

        return user
