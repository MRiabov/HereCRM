from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories import BusinessRepository
from src.models import InvoicingWorkflow, QuotingWorkflow, PaymentTiming, JobCreationDefault
from typing import Any, Dict

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
            "workflow_show_whatsapp_button": False if business.workflow_show_whatsapp_button is None else business.workflow_show_whatsapp_button,
            "workflow_pipeline_quoted_stage": business.workflow_pipeline_quoted_stage,
            "workflow_distance_unit": business.workflow_distance_unit or "mi",
            "workflow_auto_quote_followup": business.workflow_auto_quote_followup,
            "workflow_quote_followup_delay_hrs": business.workflow_quote_followup_delay_hrs,
            "workflow_auto_review_requests": business.workflow_auto_review_requests,
            "workflow_review_request_delay_hrs": business.workflow_review_request_delay_hrs,
            "workflow_review_link": business.workflow_review_link,
            "workflow_job_creation_default": business.workflow_job_creation_default or JobCreationDefault.UNSCHEDULED,
            "payment_link": business.payment_link,
            "default_city": business.default_city,
            "default_country": business.default_country,
            "default_tax_rate": business.default_tax_rate,
            "seat_count": business.seat_limit,
            "billing_cycle_anchor": business.billing_cycle_anchor,
            "marketing_settings": business.marketing_settings or {},
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
            "workflow_show_whatsapp_button",
            "workflow_pipeline_quoted_stage",
            "workflow_distance_unit",
            "workflow_auto_quote_followup",
            "workflow_quote_followup_delay_hrs",
            "workflow_auto_review_requests",
            "workflow_review_request_delay_hrs",
            "workflow_review_link",
            "payment_link",
            "workflow_job_creation_default",
            "default_city",
            "default_country",
            "default_tax_rate",
            "marketing_settings",
        }

        for key, value in settings.items():
            if key in allowed_keys:
                # Convert string values to Enums if necessary
                if key == "workflow_invoicing" and isinstance(value, str):
                    value = InvoicingWorkflow(value.upper())
                elif key == "workflow_quoting" and isinstance(value, str):
                    value = QuotingWorkflow(value.upper())
                elif key == "workflow_payment_timing" and isinstance(value, str):
                    value = PaymentTiming(value.upper())
                elif key == "workflow_job_creation_default" and isinstance(value, str):
                    value = JobCreationDefault(value.upper())
                
                setattr(business, key, value)
        
        await self.session.flush()
        return await self.get_settings(business_id)
