from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Quote, Customer, User, QuoteLineItem
from src.schemas.pwa import QuoteSchema
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

    if search:
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
    quotes = result.scalars().all()
    return quotes

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

    return quote
