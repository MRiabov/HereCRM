from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Business
from src.repositories import UserRepository, BusinessRepository


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)

    async def get_or_create_user(self, phone: str) -> User:
        """
        Retrieves a user by phone number. If not found, creates a new Business
        and a new User (Owner) linked to that business.
        """
        user = await self.user_repo.get_by_phone(phone)
        if user:
            return user

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

        return user
