import logging
import secrets
from typing import List, Dict, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models import Quote, QuoteLineItem, QuoteStatus, Job, LineItem
from datetime import datetime

logger = logging.getLogger(__name__)

class QuoteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def confirm_quote(self, token: str) -> Optional[Quote]:
        """
        Confirms a quote using its external token.
        Updates status to ACCEPTED and creates a corresponding Job.
        """
        stmt = select(Quote).options(selectinload(Quote.items)).where(Quote.external_token == token)
        result = await self.session.execute(stmt)
        quote = result.scalars().first()

        if not quote:
            return None
        
        if quote.status == QuoteStatus.ACCEPTED:
            return quote # Already accepted

        quote.status = QuoteStatus.ACCEPTED
        
        # Create Job
        job = Job(
            business_id=quote.business_id,
            customer_id=quote.customer_id,
            status="pending",
            description=f"Job from Quote #{quote.id}",
            value=quote.total_amount,
            line_items=[
                LineItem(
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total,
                    service_id=item.service_id
                ) for item in quote.items
            ]
        )
        self.session.add(job)
        await self.session.flush() # Get Job ID
        
        quote.job_id = job.id
        await self.session.commit()
        await self.session.refresh(quote)
        
        return quote

    async def create_quote(
        self, customer_id: int, business_id: int, lines: List[Dict]
    ) -> Quote:
        """
        Creates a new quote with line items.
        
        Args:
            customer_id: ID of the customer
            business_id: ID of the business
            lines: List of dicts with keys: service_id (opt), description, quantity, unit_price
        """
        logger.info(f"Creating quote for customer {customer_id}, business {business_id}")
        
        total_amount = 0.0
        quote_items = []

        for line in lines:
            quantity = line.get("quantity", 1.0)
            unit_price = line.get("unit_price", 0.0)
            line_total = quantity * unit_price
            total_amount += line_total

            item = QuoteLineItem(
                service_id=line.get("service_id"),
                description=line.get("description", ""),
                quantity=quantity,
                unit_price=unit_price,
                total=line_total,
            )
            quote_items.append(item)

        quote = Quote(
            customer_id=customer_id,
            business_id=business_id,
            status=QuoteStatus.DRAFT,
            total_amount=total_amount,
            external_token=secrets.token_urlsafe(32),
            items=quote_items,
        )

        self.session.add(quote)
        await self.session.commit()
        await self.session.refresh(quote)
        
        return quote

    async def get_quote(self, quote_id: int) -> Optional[Quote]:
        """
        Retrieves a quote by ID.
        """
        stmt = select(Quote).where(Quote.id == quote_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_recent_quote(self, customer_id: int) -> Optional[Quote]:
        """
        Returns the most recent SENT quote for a customer.
        """
        stmt = (
            select(Quote)
            .where(Quote.customer_id == customer_id, Quote.status == QuoteStatus.SENT)
            .order_by(desc(Quote.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def send_quote(self, quote_id: int) -> None:
        """
        Sends the quote to the customer via their preferred channel.
        For now, this mocks the PDF generation and delivery by updating status.
        """
        quote = await self.get_quote(quote_id)
        if not quote:
            raise ValueError(f"Quote {quote_id} not found")
        
        # TODO: Integrate with PDF generation service (WP02)
        # TODO: Integrate with MessagingService
        
        logger.info(f"Sending Quote #{quote.id} to Customer #{quote.customer_id}")
        
        quote.status = QuoteStatus.SENT
        await self.session.commit()
        await self.session.refresh(quote)
