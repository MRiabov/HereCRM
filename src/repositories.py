from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, TypeVar, Type, Optional, List
from src.models import Business, User, Customer, Job, Request, ConversationState

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int, business_id: int) -> Optional[T]:
        query = select(self.model).where(self.model.id == id, self.model.business_id == business_id)
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

class BusinessRepository(BaseRepository[Business]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Business)
    
    # Business doesn't fit the BaseRepository strict tenant pattern perfectly as it IS the tenant
    # But often we might want to get business by ID
    async def get_by_id_global(self, id: int) -> Optional[Business]:
        query = select(Business).where(Business.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Customer)

class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Job)

class ConversationStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_phone(self, phone: str) -> Optional[ConversationState]:
        query = select(ConversationState).where(ConversationState.phone_number == phone)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    def add(self, state: ConversationState):
        self.session.add(state)
