from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories import BusinessRepository
from src.models import InvoicingWorkflow, QuotingWorkflow, PaymentTiming
from typing import Any, Dict, Optional

class WorkflowSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.business_repo = BusinessRepository(session)

    async def get_settings(self, business_id: int) -> Dict[str, Any]:
        """
        Retrieves workflow settings for a business, filling in defaults if NULL.
        """
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            raise ValueError(f"Business {business_id} not found")

        return {
            "workflow_invoicing": business.workflow_invoicing or InvoicingWorkflow.MANUAL,
            "workflow_quoting": business.workflow_quoting or QuotingWorkflow.MANUAL,
            "workflow_payment_timing": business.workflow_payment_timing or PaymentTiming.USUALLY_PAID_ON_SPOT,
            "workflow_tax_inclusive": True if business.workflow_tax_inclusive is None else business.workflow_tax_inclusive,
            "workflow_include_payment_terms": False if business.workflow_include_payment_terms is None else business.workflow_include_payment_terms,
            "workflow_enable_reminders": False if business.workflow_enable_reminders is None else business.workflow_enable_reminders,
            "payment_link": business.payment_link,
        }

    async def update_settings(self, business_id: int, **settings) -> Dict[str, Any]:
        """
        Updates workflow settings for a business.
        """
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            raise ValueError(f"Business {business_id} not found")

        allowed_keys = {
            "workflow_invoicing",
            "workflow_quoting",
            "workflow_payment_timing",
            "workflow_tax_inclusive",
            "workflow_include_payment_terms",
            "workflow_enable_reminders",
            "payment_link",
        }

        for key, value in settings.items():
            if key in allowed_keys:
                setattr(business, key, value)
        
        await self.session.flush()
        return await self.get_settings(business_id)
