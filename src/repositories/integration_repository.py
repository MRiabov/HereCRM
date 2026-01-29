from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from src.models import IntegrationConfig, IntegrationType
from .base import BaseRepository


class IntegrationRepository(BaseRepository[IntegrationConfig]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, IntegrationConfig)

    async def get_active_by_type(
        self, business_id: int, type: IntegrationType
    ) -> List[IntegrationConfig]:
        """Return list of active configs for a given type for a specific business."""
        query = select(self.model).where(
            self.model.business_id == business_id,
            self.model.type == type,
            self.model.is_active.is_(True),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_key_hash(self, key_hash: str) -> Optional[IntegrationConfig]:
        """Specific lookup for authentication across all businesses (keys are unique)."""
        query = select(self.model).where(
            self.model.key_hash == key_hash, self.model.is_active.is_(True)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
