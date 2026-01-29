from src.models import JobStatus
import logging
import secrets
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models import (
    Quote,
    QuoteLineItem,
    QuoteStatus,
    Job,
    LineItem,
    Request,
    Business,
    Customer,
    MessageTriggerSource,
)
from src.services.pdf_generator import pdf_generator
from src.services.storage import storage_service
from src.services.tax_calculator import tax_calculator

logger = logging.getLogger(__name__)


class QuoteService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.s3_service = storage_service
        self.pdf_generator = pdf_generator

    async def confirm_quote(self, token: str) -> Optional[Quote]:
        """
        Confirms a quote using its external token.
        Updates status to ACCEPTED and creates a corresponding Job.
        """
        stmt = (
            select(Quote)
            .options(selectinload(Quote.items))
            .where(Quote.external_token == token)
        )
        result = await self.session.execute(stmt)
        quote = result.scalars().first()

        if not quote:
            return None

        if quote.status == QuoteStatus.ACCEPTED:
            return quote  # Already accepted

        quote.status = QuoteStatus.ACCEPTED

        # Create Job
        job = Job(
            business_id=quote.business_id,
            customer_id=quote.customer_id,
            status=JobStatus.PENDING,
            description=f"Job from Quote #{quote.id}",
            value=quote.total_amount,
            subtotal=quote.subtotal,
            tax_amount=quote.tax_amount,
            tax_rate=quote.tax_rate,
            line_items=[
                LineItem(
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total,
                    service_id=item.service_id,
                )
                for item in quote.items
            ],
        )
        self.session.add(job)
        await self.session.flush()  # Get Job ID

        quote.job_id = job.id
        await self.session.commit()
        await self.session.refresh(quote)

        from src.events import QUOTE_ACCEPTED, event_bus

        await event_bus.emit(
            QUOTE_ACCEPTED,
            {
                "quote_id": quote.id,
                "business_id": quote.business_id,
                "customer_id": quote.customer_id,
            },
        )

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
        logger.info(
            f"Creating quote for customer {customer_id}, business {business_id}"
        )

        # Fetch business to check tax settings
        business = await self.session.get(Business, business_id)
        if not business:
            raise ValueError(f"Business {business_id} not found")

        # Fetch customer (for future location-based tax)
        customer = await self.session.get(Customer, customer_id)

        # Calculate taxes
        tax_result = tax_calculator.calculate_quote_tax(lines, business, customer)

        quote_items = []
        for line in lines:
            quantity = line.get("quantity", 1.0)
            unit_price = line.get("unit_price", 0.0)
            line_total = quantity * unit_price

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
            total_amount=tax_result["total_amount"],
            subtotal=tax_result["subtotal"],
            tax_amount=tax_result["tax_amount"],
            tax_rate=tax_result["tax_rate"],
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
        Generates PDF, uploads to S3, and updates status.
        """
        quote = await self.get_quote(quote_id)
        if not quote:
            raise ValueError(f"Quote {quote_id} not found")

        logger.info(f"Generating PDF for Quote #{quote.id}")

        try:
            # Generate PDF
            pdf_bytes = self.pdf_generator.generate_quote(quote)

            # Upload to S3
            filename = f"quotes/quote_{quote.id}_{int(datetime.now().timestamp())}.pdf"
            public_url = self.s3_service.upload_file(
                file_content=pdf_bytes, key=filename, content_type="application/pdf"
            )

            quote.blob_url = public_url
            logger.info(f"Quote PDF uploaded to {public_url}")

        except Exception as e:
            logger.error(f"Failed to generate or upload PDF for quote {quote.id}: {e}")
            # We raise error to indicate failure
            raise RuntimeError(f"Failed to process quote PDF: {e}") from e

        # Integrate with MessagingService (send the public_url)
        from src.services.messaging_service import messaging_service
        from src.repositories import CustomerRepository
        from src.events import QUOTE_SENT, event_bus

        customer_repo = CustomerRepository(self.session)
        customer = await customer_repo.get_by_id(quote.customer_id, quote.business_id)

        if customer and customer.phone:
            content = f"Here is your quote from {customer.business.name}: {public_url}"
            await messaging_service.enqueue_message(
                recipient_phone=customer.phone,
                content=content,
                trigger_source=MessageTriggerSource.QUOTE_SENT,
                business_id=quote.business_id,
            )

        logger.info(f"Sending Quote #{quote.id} to Customer #{quote.customer_id}")

        quote.status = QuoteStatus.SENT
        await self.session.commit()
        await self.session.refresh(quote)

        # Emit event for follow-up scheduling
        await event_bus.emit(
            QUOTE_SENT,
            {
                "quote_id": quote.id,
                "customer_id": quote.customer_id,
                "business_id": quote.business_id,
                "total_amount": quote.total_amount,
            },
        )

    async def create_from_request(
        self, request_id: int, customer_id: int, items: Optional[List[Dict]] = None
    ) -> Quote:
        """
        Promotes a customer request to a quote.
        """
        stmt = (
            select(Request)
            .options(selectinload(Request.line_items))
            .where(Request.id == request_id)
        )
        result = await self.session.execute(stmt)
        request = result.scalars().first()

        if not request:
            raise ValueError(f"Request {request_id} not found")

        # Use request's line items if no items provided
        if not items and request.line_items:
            items = [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "service_id": item.service_id,
                }
                for item in request.line_items
            ]

        # Reuse create_quote logic if items provided
        if items:
            quote = await self.create_quote(customer_id, request.business_id, items)
            # Add a reference to the source request in description if possible
            # (Quote model doesn't have a long description, but QuoteLineItem has)
        else:
            # Create a draft quote with a single descriptive item from the request description
            quote = await self.create_quote(
                customer_id,
                request.business_id,
                [
                    {
                        "description": f"Request: {request.description}",
                        "quantity": 1,
                        "unit_price": 0.0,
                    }
                ],
            )

        # Update request status instead of deleting (or follow Job conversion pattern)
        # CRMService.convert_request deletes the request, so we should probably follow that.
        # But we'll let CRMService handle the deletion to match the 'schedule' action pattern.

        return quote
