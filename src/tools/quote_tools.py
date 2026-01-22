import logging
from typing import Optional, Tuple, Dict, Any
from src.uimodels import CreateQuoteInput
from src.services.quote_service import QuoteService
from src.repositories import CustomerRepository
from src.services.template_service import TemplateService

logger = logging.getLogger(__name__)

class CreateQuoteTool:
    def __init__(self, quote_service: QuoteService, customer_repo: CustomerRepository, business_id: int, template_service: TemplateService):
        self.quote_service = quote_service
        self.customer_repo = customer_repo
        self.business_id = business_id
        self.template_service = template_service

    async def run(self, input: CreateQuoteInput) -> Tuple[str, Optional[Dict[str, Any]]]:
        # 1. Resolve Customer
        customers = await self.customer_repo.search(input.customer_identifier, self.business_id)
        if not customers:
             return f"Could not find customer matching '{input.customer_identifier}'", None
        if len(customers) > 1:
             return f"Multiple customers found matching '{input.customer_identifier}'. Please be more specific.", None
        
        customer = customers[0]
        
        # 2. Prepare Line Items
        lines = []
        for item in input.items:
            lines.append({
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.price,
                # service_id could be resolved if we had a mechanism, for now assume ad-hoc
            })

        # 3. Create Quote
        quote = await self.quote_service.create_quote(
            customer_id=customer.id,
            business_id=self.business_id,
            lines=lines
        )

        # 4. Send Quote
        try:
            # We call send_quote if it exists. 
            # Note: This relies on WP02 implementation of QuoteService.send_quote
            if hasattr(self.quote_service, 'send_quote'):
                await self.quote_service.send_quote(quote.id)
                msg = self.template_service.render(
                    "job_added", 
                    category="Quote", 
                    name=customer.name, 
                    location="", 
                    price_info=f" (Total: {quote.total_amount})"
                )
            else:
                 msg = self.template_service.render(
                    "job_added", 
                    category="Quote", 
                    name=customer.name, 
                    location="", 
                    price_info=f" (Total: {quote.total_amount}) - PDF sending not enabled"
                )
                 
        except Exception as e:
            logger.error(f"Failed to send quote: {e}")
            msg = f"Quote #{quote.id} created for {customer.name}, but failed to send: {e}"

        return msg, {
            "action": "create_quote",
            "entity": "quote",
            "id": quote.id,
            "customer": customer.name,
            "total": quote.total_amount
        }
