from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Invoice, Job, Customer, User
from src.schemas.pwa import InvoiceSchema
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[InvoiceSchema])
async def list_invoices(
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve invoices with Job and Customer info
    stmt = (
        select(Invoice)
        .join(Job)
        .join(Customer)
        .where(Job.business_id == current_user.business_id)
        .options(
            joinedload(Invoice.job).joinedload(Job.customer)
        )
    )

    if search:
        # Search by Invoice ID (if numeric), Customer Name, or Job Description
        search_filters = [
            Customer.name.ilike(f"%{search}%"),
            Job.description.ilike(f"%{search}%")
        ]
        if search.isdigit():
            search_filters.append(Invoice.id == int(search))
        
        stmt = stmt.where(or_(*search_filters))

    stmt = stmt.order_by(desc(Invoice.created_at))
    
    result = await session.execute(stmt)
    invoices = result.scalars().all()

    response = []
    for inv in invoices:
        # Populate schema fields
        # InvoiceSchema needs: id, job_id, total_amount, status, created_at, public_url, customer_name
        response.append(InvoiceSchema(
            id=inv.id,
            job_id=inv.job_id,
            total_amount=inv.job.value or 0.0,
            status=inv.status,
            created_at=inv.created_at,
            public_url=inv.public_url,
            customer_name=inv.job.customer.name if inv.job and inv.job.customer else "Unknown"
        ))
    return response

@router.get("/{invoice_id}", response_model=InvoiceSchema)
async def get_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(Invoice)
        .join(Job)
        .options(
            joinedload(Invoice.job).joinedload(Job.customer)
        )
        .where(Invoice.id == invoice_id, Job.business_id == current_user.business_id)
    )
    result = await session.execute(stmt)
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return InvoiceSchema(
        id=invoice.id,
        job_id=invoice.job_id,
        total_amount=invoice.job.value or 0.0,
        status=invoice.status,
        created_at=invoice.created_at,
        public_url=invoice.public_url,
        customer_name=invoice.job.customer.name if invoice.job and invoice.job.customer else "Unknown"
    )
