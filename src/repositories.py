from sqlalchemy import select, or_, and_, event, func
from sqlalchemy.orm import joinedload, contains_eager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, TypeVar, Type, Optional, List, Any
from datetime import datetime
from src.models import (
    Business,
    User,
    Customer,
    Job,
    Request,
    ConversationState,
    PipelineStage,
    Service,
    LineItem,
)
import math
import re

def normalize_phone(phone: str) -> str:
    """Standardize phone number by removing whitespace and dashes."""
    if not phone:
        return phone
    return re.sub(r'[\s\-]', '', phone)


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

    async def get_by_id(self, user_id: int) -> Optional[User]:
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        # This is GLOBAL lookup to identify the user
        phone = normalize_phone(phone)
        query = select(User).where(User.phone_number == phone)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).where(User.email.ilike(email))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, user: User):
        if user.phone_number:
            user.phone_number = normalize_phone(user.phone_number)
        self.session.add(user)

    async def update_preferences(
        self, user_id: int, key: str, value: Any
    ) -> Optional[Any]:
        user = await self.get_by_id(user_id)
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

    async def get_by_name(self, name: str, business_id: int) -> Optional[Service]:
        query = select(Service).where(
            Service.name.ilike(name), Service.business_id == business_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

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
        phone = normalize_phone(phone)
        query = select(Customer).where(
            Customer.phone == phone, Customer.business_id == business_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def add(self, item: Customer):
        if item.name:
            item.name = item.name.title()
        if item.phone:
            item.phone = normalize_phone(item.phone)
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
        pipeline_stage: Optional[str] = None,
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
            norm_query = normalize_phone(query)
            conditions.append(
                or_(
                    Customer.name.ilike(f"%{query}%"),
                    Customer.phone.ilike(f"%{norm_query}%"),
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

        # Pipeline Stage filter
        if pipeline_stage:
            conditions.append(Customer.pipeline_stage == pipeline_stage)

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

    async def get_pipeline_summary(self, business_id: int, example_limit: int = 5) -> dict[PipelineStage, dict]:
        # Aggregate counts directly in the database
        count_stmt = (
            select(Customer.pipeline_stage, func.count(Customer.id))
            .where(Customer.business_id == business_id)
            .group_by(Customer.pipeline_stage)
        )
        result = await self.session.execute(count_stmt)
        counts = dict(result.all())

        summary = {}
        for stage in PipelineStage:
            # Fetch up to `example_limit` examples for each stage
            example_stmt = (
                select(Customer)
                .where(Customer.business_id == business_id, Customer.pipeline_stage == stage)
                .limit(example_limit)
            )
            example_result = await self.session.execute(example_stmt)
            examples = list(example_result.scalars().all())

            summary[stage] = {
                "count": counts.get(stage, 0),
                "examples": examples
            }
        return summary


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

        # Spatial Filtering Optimization
        if center_lat is not None and center_lon is not None and radius:
            deg_rad = math.degrees(radius / 6371000)
            lat_min, lat_max = center_lat - deg_rad, center_lat + deg_rad
            lon_delta = deg_rad / math.cos(math.radians(center_lat)) if abs(center_lat) < 89 else 180
            lon_min, lon_max = center_lon - lon_delta, center_lon + lon_delta

            eff_lat, eff_lon = func.coalesce(Job.latitude, Customer.latitude), func.coalesce(Job.longitude, Customer.longitude)
            conditions.append(eff_lat.between(lat_min, lat_max))
            conditions.append(eff_lon.between(lon_min, lon_max))

            stmt = select(Job).outerjoin(Job.customer).options(
                contains_eager(Job.customer), joinedload(Job.line_items)
            ).where(and_(*conditions))
        else:
            stmt = select(Job).options(joinedload(Job.customer), joinedload(Job.line_items)).where(and_(*conditions))

        result = await self.session.execute(stmt)
        jobs = list(result.scalars().unique().all())

        # Fine-grained Spatial Filtering (Python-side)
        if center_lat is not None and center_lon is not None and radius:
            filtered = []
            for j in jobs:
                j_lat, j_lon = j.latitude, j.longitude
                
                if j_lat is None or j_lon is None:
                    if j.customer and j.customer.latitude is not None and j.customer.longitude is not None:
                        j_lat, j_lon = j.customer.latitude, j.customer.longitude

                if j_lat is not None and j_lon is not None:
                    dist = haversine_distance(
                        center_lat, center_lon, j_lat, j_lon
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

    async def get_count_by_customer(self, customer_id: int, business_id: int) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).where(
            Job.customer_id == customer_id, Job.business_id == business_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

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

    async def get_by_user_id(self, user_id: int) -> Optional[ConversationState]:
        query = select(ConversationState).where(ConversationState.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int) -> ConversationState:
        state = await self.get_by_user_id(user_id)
        if not state:
            state = ConversationState(user_id=user_id)
            self.add(state)
            await self.session.flush()
        return state

    def add(self, state: ConversationState):
        self.session.add(state)


# Event Listeners for Job Value Synchronization
def update_job_value(mapper, connection, target):
    # Recalculate and sync job value
    job_id = target.job_id
    if not job_id:
        return

    # Use a direct SQL update for the database
    # We use a scalar subquery to get the sum of line items
    # To avoid MissingGreenlet, we ensure we use the connection correctly
    try:
        # Calculate new total using a subquery that is compatible with direct execution
        # Note: We use the connection directly to avoid session-related lazy loading
        result = connection.execute(
            select(func.sum(LineItem.total_price))
            .where(LineItem.job_id == job_id)
        )
        new_total = result.scalar() or 0.0

        connection.execute(
            Job.__table__.update()
            .where(Job.id == job_id)
            .values(value=new_total)
        )

        # Stale Object State Fix: Update the Job object in the session if it exists
        from sqlalchemy.orm import object_session
        session = object_session(target)
        if session:
            # Look for the job in the identity map to avoid a fresh DB query/lazy load
            from sqlalchemy.orm.util import identity_key
            from sqlalchemy.orm.attributes import set_committed_value
            key = identity_key(Job, (job_id,))
            job = session.identity_map.get(key)
            if job:
                # Update the object attribute directly without marking as dirty
                set_committed_value(job, "value", new_total)
    except Exception:
        # Listeners should be robust
        pass

event.listen(LineItem, "after_insert", update_job_value)
event.listen(LineItem, "after_update", update_job_value)
event.listen(LineItem, "after_delete", update_job_value)
