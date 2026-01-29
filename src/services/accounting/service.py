import logging
from sqlalchemy.ext.asyncio import AsyncSession
from .quickbooks_sync import QuickBooksSyncManager

logger = logging.getLogger(__name__)


class AccountingService:
    """Facade for all accounting-related operations (QuickBooks)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sync_manager = QuickBooksSyncManager(session)

    async def trigger_manual_sync(self, business_id: int):
        """
        Triggers a manual synchronization for a business.
        Returns the created SyncLog.
        """
        logger.info(f"Manual sync triggered for business {business_id}")
        return await self.sync_manager.trigger_manual_sync(business_id)
