import logging
from typing import Optional, Tuple, Dict, Any
from src.uimodels import CreateQuoteInput
from src.services.quote_service import QuoteService
from src.repositories import CustomerRepository

logger = logging.getLogger(__name__)

class CreateQuoteTool:
    def __init__(self, quote_service: QuoteService, customer_repo: CustomerRepository, business_id: int):
        self.quote_service = quote_service
        self.customer_repo = customer_repo
        self.business_id = business_id

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
                msg = f"Quote #{quote.id} created and sent to {customer.name} via WhatsApp."
            else:
                 msg = f"Quote #{quote.id} created for {customer.name}. (Note: PDF sending not enabled)"
                 
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
