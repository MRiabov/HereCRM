import logging
import json
import httpx
from typing import Any
from src.database import AsyncSessionLocal
from src.repositories.integration_repository import IntegrationRepository
from src.repositories import JobRepository, CustomerRepository
from src.models.integration_config import IntegrationType
from src.utils.security import Signer
from src.events import event_bus, JOB_BOOKED

logger = logging.getLogger(__name__)

class IntegrationEventHandler:
    @event_bus.on(JOB_BOOKED)
    @staticmethod
    async def handle_job_booked(data: dict) -> None:
        """
        Subscriber for JOB_BOOKED event.
        Dispatches webhooks and Meta CAPI events.
        """
        job_id = data.get("job_id")
        business_id = data.get("business_id")
        
        if not job_id or not business_id:
            logger.error("Missing job_id or business_id in JOB_BOOKED event")
            return

        async with AsyncSessionLocal() as session:
            integration_repo = IntegrationRepository(session)
            job_repo = JobRepository(session)
            customer_repo = CustomerRepository(session)
            
            # Fetch Job with line items and customer
            job = await job_repo.get_with_line_items(job_id, business_id)
            if not job:
                logger.error(f"Job {job_id} not found for integration dispatch")
                return
            
            customer = job.customer
            if not customer:
                # Fallback if relationship not loaded or missing
                customer = await customer_repo.get_by_id(job.customer_id, business_id)
            
            # 1. Handle Generic Webhooks
            webhook_configs = await integration_repo.get_active_by_type(business_id, IntegrationType.WEBHOOK)
            for config in webhook_configs:
                try:
                    await IntegrationEventHandler._dispatch_webhook(config, job, customer)
                except Exception as e:
                    logger.error(f"Failed to dispatch webhook {config.id}: {e}", exc_info=True)

    @staticmethod
    async def _dispatch_webhook(config: Any, job: Any, customer: Any) -> None:
        url = config.config_payload.get("url")
        secret = config.config_payload.get("signing_secret")
        
        if not url:
            logger.warning(f"Webhook config {config.id} missing URL")
            return

        # Prepare payload
        payload = {
            "event": "job.booked",
            "job": {
                "id": job.id,
                "description": job.description,
                "value": job.value,
                "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
                "location": job.location,
            },
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
            } if customer else None,
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                } for item in job.line_items
            ]
        }
        
        payload_str = json.dumps(payload)
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "HereCRM-Webhook-Dispatcher/1.0",
        }
        
        if secret:
            signature = Signer.sign(payload_str, secret)
            headers["X-HereCRM-Signature"] = signature

        async with httpx.AsyncClient() as client:
            response = await client.post(url, content=payload_str, headers=headers, timeout=10.0)
            if response.status_code >= 400:
                logger.error(f"Webhook {url} returned status {response.status_code}: {response.text}")
            else:
                logger.info(f"Successfully dispatched webhook to {url}")
