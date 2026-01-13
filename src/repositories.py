from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, TypeVar, Type, Optional, List, Any
from src.models import Business, User, Customer, Job, Request, ConversationState

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int, business_id: int) -> Optional[T]:
        query = select(self.model).where(
            self.model.id == id, self.model.business_id == business_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, business_id: int) -> List[T]:
        query = select(self.model).where(self.model.business_id == business_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    def add(self, item: T):
        self.session.add(item)
        # Note: commit should be handled by the service layer or unit of work


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_phone(self, phone: str) -> Optional[User]:
        # This is GLOBAL lookup to identify the user
        query = select(User).where(User.phone_number == phone)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, user: User):
        self.session.add(user)

    async def update_preferences(
        self, phone: str, key: str, value: Any
    ) -> Optional[Any]:
        user = await self.get_by_phone(phone)
        if not user:
            return None

        old_value = (user.preferences or {}).get(key)

        # Update preferences
        prefs = dict(user.preferences or {})
        prefs[key] = value
        user.preferences = prefs
        return old_value


class BusinessRepository(BaseRepository[Business]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Business)

    # Business doesn't fit the BaseRepository strict tenant pattern perfectly as it IS the tenant
    # But often we might want to get business by ID
    async def get_by_id_global(self, id: int) -> Optional[Business]:
        query = select(Business).where(Business.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, business: Business):
        self.session.add(business)


class RequestRepository(BaseRepository[Request]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Request)

    async def search(self, query: str, business_id: int) -> List[Request]:
        stmt = select(Request).where(
            Request.business_id == business_id, Request.content.ilike(f"%{query}%")
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Customer)

    async def get_by_name(self, name: str, business_id: int) -> Optional[Customer]:
        query = select(Customer).where(
            Customer.name == name, Customer.business_id == business_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str, business_id: int) -> Optional[Customer]:
        query = select(Customer).where(
            Customer.phone == phone, Customer.business_id == business_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def search(self, query: str, business_id: int) -> List[Customer]:
        stmt = select(Customer).where(
            Customer.business_id == business_id,
            or_(Customer.name.ilike(f"%{query}%"), Customer.phone.ilike(f"%{query}%")),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Job)

    async def search(self, query: str, business_id: int) -> List[Job]:
        stmt = select(Job).where(
            Job.business_id == business_id, Job.description.ilike(f"%{query}%")
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_most_recent_by_customer(
        self, customer_id: int, business_id: int
    ) -> Optional[Job]:
        stmt = (
            select(Job)
            .where(Job.customer_id == customer_id, Job.business_id == business_id)
            .order_by(Job.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ConversationStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_phone(self, phone: str) -> Optional[ConversationState]:
        query = select(ConversationState).where(ConversationState.phone_number == phone)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, state: ConversationState):
        self.session.add(state)
