import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Quote, Customer, User, QuoteLineItem, QuoteStatus
from src.schemas.pwa import QuoteSchema, QuoteCreate
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[QuoteSchema])
async def list_quotes(
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(Quote)
        .where(Quote.business_id == current_user.business_id)
        .options(
            joinedload(Quote.customer),
            joinedload(Quote.items)
        )
    )

    ignore_keywords = ["all", "quotes", "show quotes", "show all quotes", "list quotes"]
    if search and search.strip().lower() not in ignore_keywords:
        search_filters = [
            Customer.name.ilike(f"%{search}%"),
        ]
        if search.isdigit():
            search_filters.append(Quote.id == int(search))
        
        # Also search in line items
        stmt = stmt.join(Quote.customer).outerjoin(Quote.items)
        search_filters.append(QuoteLineItem.description.ilike(f"%{search}%"))
        
        stmt = stmt.where(or_(*search_filters))
    else:
        stmt = stmt.join(Quote.customer)

    stmt = stmt.order_by(desc(Quote.created_at)).distinct()
    
    result = await session.execute(stmt)
    quotes = result.scalars().unique().all()
    
    response = []
    for q in quotes:
        response.append(QuoteSchema(
            id=q.id,
            customer_id=q.customer_id,
            quote_number=f"QT-{q.id:03d}",
            total_amount=q.total_amount,
            status=q.status,
            external_token=q.external_token,
            public_url=q.blob_url,
            created_at=q.created_at,
            items=[{
                "id": i.id,
                "description": i.description,
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "total": i.total,
                "service_id": i.service_id
            } for i in q.items],
            customer=q.customer
        ))
    return response

@router.get("/{quote_id}", response_model=QuoteSchema)
async def get_quote(
    quote_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(Quote)
        .options(
            joinedload(Quote.customer),
            joinedload(Quote.items)
        )
        .where(Quote.id == quote_id, Quote.business_id == current_user.business_id)
    )
    result = await session.execute(stmt)
    quote = result.scalar_one_or_none()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    return QuoteSchema(
        id=quote.id,
        customer_id=quote.customer_id,
        quote_number=f"QT-{quote.id:03d}",
        total_amount=quote.total_amount,
        status=quote.status,
        external_token=quote.external_token,
        public_url=quote.blob_url,
        created_at=quote.created_at,
        items=[{
            "id": i.id,
            "description": i.description,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
            "total": i.total,
            "service_id": i.service_id
        } for i in quote.items],
        customer=quote.customer
    )

@router.post("/", response_model=QuoteSchema)
async def create_quote(
    quote_in: QuoteCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify customer belongs to business
    customer_stmt = select(Customer).where(
        Customer.id == quote_in.customer_id,
        Customer.business_id == current_user.business_id
    )
    customer_res = await session.execute(customer_stmt)
    customer = customer_res.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Calculate total
    total = 0.0
    line_items = []
    for item in quote_in.items:
        qty = float(item.quantity)
        price = float(item.unit_price)
        item_total = qty * price
        total += item_total
        
        line_items.append(QuoteLineItem(
            description=item.description,
            quantity=qty,
            unit_price=price,
            total=item_total,
            service_id=item.service_id
        ))

    quote = Quote(
        customer_id=quote_in.customer_id,
        business_id=current_user.business_id,
        title=quote_in.title,
        location=quote_in.location,
        notes=quote_in.notes,
        total_amount=quote_in.total_amount or total,
        status=QuoteStatus(quote_in.status),
        external_token=uuid.uuid4().hex,
        items=line_items
    )

    session.add(quote)
    await session.commit()
    await session.refresh(quote)
    
    # Reload with items and customer for response
    stmt = (
        select(Quote)
        .options(
            joinedload(Quote.customer),
            joinedload(Quote.items)
        )
        .where(Quote.id == quote.id)
    )
    result = await session.execute(stmt)
    q = result.scalar_one()
    
    return QuoteSchema(
        id=q.id,
        customer_id=q.customer_id,
        quote_number=f"QT-{q.id:03d}",
        total_amount=q.total_amount,
        status=q.status,
        external_token=q.external_token,
        public_url=q.blob_url,
        created_at=q.created_at,
        items=[{
            "id": i.id,
            "description": i.description,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
            "total": i.total,
            "service_id": i.service_id
        } for i in q.items],
        customer=q.customer
    )

