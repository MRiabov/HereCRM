from sqlalchemy import select, or_, and_, event, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, TypeVar, Type, Optional, List, Any
from datetime import datetime
from src.models import Business, User, Customer, Job, Request, ConversationState, Service, LineItem
import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two coordinates."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


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
        return list(result.scalars().all())

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


class ServiceRepository(BaseRepository[Service]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Service)

    async def get_all_for_business(self, business_id: int) -> List[Service]:
        return await self.get_all(business_id)

    async def update(self, service_id: int, business_id: int, **kwargs) -> Optional[Service]:
        service = await self.get_by_id(service_id, business_id)
        if not service:
            return None

        allowed_fields = {"name", "description", "default_price"}
        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(service, key):
                setattr(service, key, value)
        return service

    async def delete(self, service_id: int, business_id: int) -> bool:
        service = await self.get_by_id(service_id, business_id)
        if not service:
            return False
        await self.session.delete(service)
        return True


class RequestRepository(BaseRepository[Request]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Request)

    async def search(
        self,
        query: str,
        business_id: int,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> List[Request]:
        conditions = [Request.business_id == business_id]

        if query and query.strip().lower() not in ["all", "requests", "show requests"]:
            conditions.append(Request.content.ilike(f"%{query}%"))

        if status:
            conditions.append(Request.status == status)

        if min_date:
            conditions.append(Request.created_at >= min_date)
        if max_date:
            conditions.append(Request.created_at <= max_date)

        stmt = select(Request).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Customer)

    async def get_by_name(self, name: str, business_id: int) -> Optional[Customer]:
        query = select(Customer).where(
            Customer.name.ilike(name), Customer.business_id == business_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str, business_id: int) -> Optional[Customer]:
        # Phone numbers can be tricky, but for now we'll do literal match or maybe strip spaces/dashes?
        # User asked for deduplication robustness. Let's just do exact map for phone for now as 'ilike' for phone is weird.
        # But wait, plan says "case-insensitive". For phone that doesn't matter much unless letters are used.
        query = select(Customer).where(
            Customer.phone == phone, Customer.business_id == business_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, item: Customer):
        if item.name:
            item.name = item.name.title()
        super().add(item)

    async def search(
        self,
        query: str,
        business_id: int,
        entity_type: Optional[str] = None,
        query_type: Optional[str] = None,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        radius: Optional[float] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        center_address: Optional[str] = None,
    ) -> List[Customer]:
        conditions = [Customer.business_id == business_id]

        # Name/Phone Text Search
        ignore_keywords = [
            "all",
            "customers",
            "leads",
            "show leads",
            "show customers",
            "show all",
            "all leads",
            "all customers",
            "all clients",
            "clients",
            "show all clients",
            "show all customers",
            "show active customers",
        ]
        if query and query.strip().lower() not in ignore_keywords:
            conditions.append(
                or_(
                    Customer.name.ilike(f"%{query}%"),
                    Customer.phone.ilike(f"%{query}%"),
                    Customer.street.ilike(f"%{query}%"),
                    Customer.city.ilike(f"%{query}%"),
                    Customer.original_address_input.ilike(f"%{query}%"),
                )
            )

        # Query Type logic (Precedence over generic entity type)
        if query_type == "scheduled":
            # "Customers with jobs today"
            # We need customers who have jobs in the date range
            stmt = select(Customer).join(Job)
            if min_date:
                conditions.append(Job.scheduled_at >= min_date)
            if max_date:
                conditions.append(Job.scheduled_at <= max_date)
            # IMPORTANT: We are searching for customers, but filtering by JOB properties

        # Entity Type logic (Lead VS generic Customer)
        elif entity_type == "lead" or (query and "lead" in query.lower()):
            # A lead is a customer with 0 jobs.
            # We need a left join on Job to verify count or null
            stmt = select(Customer).outerjoin(Job)
            conditions.append(Job.id.is_(None))
        elif entity_type == "customer":
            # Explicitly customer means HAS jobs? or just anyone?
            # Usually strict "customer" implies having bought something, but for simplicity
            # let's assume it means ANYONE unless "leads" is specified
            stmt = select(Customer).outerjoin(Job)
        else:
            stmt = select(Customer)

        # "Added" query type (Created At filter)
        if query_type == "added":
            if min_date:
                conditions.append(Customer.created_at >= min_date)
            if max_date:
                conditions.append(Customer.created_at <= max_date)

        # Combine all DB conditions
        stmt = stmt.where(and_(*conditions)).distinct()

        result = await self.session.execute(stmt)
        customers = list(result.scalars().all())

        # Spatial Filtering (Python-side)
        if center_lat is not None and center_lon is not None and radius:
            filtered = []
            for c in customers:
                if c.latitude is not None and c.longitude is not None:
                    dist = haversine_distance(
                        center_lat, center_lon, c.latitude, c.longitude
                    )
                    if dist <= radius:
                        filtered.append(c)
            return filtered

        return customers

    async def get_leads(self, business_id: int) -> List[Customer]:
        return await self.search(
            query="all", business_id=business_id, entity_type="lead"
        )


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Job)

    async def search(
        self,
        query: str,
        business_id: int,
        query_type: Optional[str] = None,  # "scheduled" or "added"
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        status: Optional[str] = None,
        radius: Optional[float] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        center_address: Optional[str] = None,
    ) -> List[Job]:
        conditions = [Job.business_id == business_id]

        ignore_keywords = ["all", "jobs", "show jobs", "show all jobs", "list jobs"]
        if query and query.strip().lower() not in ignore_keywords:
            conditions.append(
                or_(
                    Job.description.ilike(f"%{query}%"),
                    Job.location.ilike(f"%{query}%"),
                )
            )

        if status:
            conditions.append(Job.status == status)

        # Date Filtering
        date_column = Job.scheduled_at  # Default to scheduled
        if query_type == "added":
            date_column = Job.created_at

        if min_date:
            conditions.append(date_column >= min_date)
        if max_date:
            conditions.append(date_column <= max_date)

        stmt = select(Job).options(joinedload(Job.customer)).where(and_(*conditions))
        result = await self.session.execute(stmt)
        jobs = list(result.scalars().all())

        # Spatial Filtering (Python-side)
        if center_lat is not None and center_lon is not None and radius:
            filtered = []
            for j in jobs:
                # Job has latitude/longitude fields directly
                if j.latitude is not None and j.longitude is not None:
                    dist = haversine_distance(
                        center_lat, center_lon, j.latitude, j.longitude
                    )
                    if dist <= radius:
                        filtered.append(j)
            return filtered

        return jobs

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

    async def get_with_line_items(self, job_id: int, business_id: int) -> Optional[Job]:
        stmt = (
            select(Job)
            .options(joinedload(Job.line_items), joinedload(Job.customer))
            .where(Job.id == job_id, Job.business_id == business_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    def add(self, item: Job):
        super().add(item)


class ConversationStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_phone(self, phone: str) -> Optional[ConversationState]:
        query = select(ConversationState).where(ConversationState.phone_number == phone)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, state: ConversationState):
        self.session.add(state)


# Event Listeners for Job Value Synchronization
def update_job_value(mapper, connection, target):
    # This runs synchronously in the flush transaction
    # We need to recalculate the job value.
    # Target is the LineItem instance.
    job_id = target.job_id
    
    # We execute a direct SQL update to avoid object session confusion during flush
    # Sum all line items for this job
    connection.execute(
        Job.__table__.update()
        .where(Job.id == job_id)
        .values(
            value=select(func.sum(LineItem.total_price))
            .where(LineItem.job_id == job_id)
            .scalar_subquery()
        )
    )

event.listen(LineItem, "after_insert", update_job_value)
event.listen(LineItem, "after_update", update_job_value)
event.listen(LineItem, "after_delete", update_job_value)
