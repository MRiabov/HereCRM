from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, TypeVar, Type, Optional, List
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

    async def get_all(self, business_id: int, skip: int = 0, limit: int = 100) -> List[T]:
        query = select(self.model).where(self.model.business_id == business_id).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    def add(self, item: T):
        self.session.add(item)
