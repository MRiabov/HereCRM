from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.models import Invoice, Customer
from src.schemas.pwa import InvoiceSchema

router = APIRouter()

@router.get("/", response_model=List[InvoiceSchema])
async def list_invoices(
    session: AsyncSession = Depends(get_db)
):
    # HARDCODED BUSINESS ID = 1
    # Simple query for all invoices for the business
    # We join with Job -> Customer to get customer name if we want to enrich
    
    query = (
        select(Invoice)
        .join(Invoice.job)
        .options(selectinload(Invoice.job).selectinload(Customer.jobs)) # Complex loading might be needed
        # Actually, let's just join Job and Customer
        .join(Customer, Invoice.job.has(Customer.id == Invoice.job_id)) # logic might be weird, easier:
        # Invoice -> Job -> Customer
        # .options(selectinload(Invoice.job).selectinload(Job.customer))
        .order_by(Invoice.created_at.desc())
        .limit(50)
    )
    # Simplify for now: Just get invoices and let Pydantic try to fetch? NO, async doesn't like lazy load
    # Explicit load
    from src.models import Job
    from src.models import Job
    query = (
        select(Invoice)
        .options(selectinload(Invoice.job).selectinload(Job.customer))
        .order_by(Invoice.created_at.desc())
        .limit(50)
    )
    
    result = await session.execute(query)
    invoices = result.scalars().all()
    
    # Map to schema
    output = []
    for inv in invoices:
        output.append(InvoiceSchema(
            id=inv.id,
            job_id=inv.job_id,
            total_amount=0.0, # TODO: Invoice model doesn't have total_amount stored directly? Check model.
            # Model check: Invoice has s3_key, public_url, payment_link, status. 
            # Payment has amount. Job has value. 
            # We can use Job value or sum line items.
            # Assuming Job value for now.
            status=inv.status,
            created_at=inv.created_at,
            public_url=inv.public_url,
            customer_name=inv.job.customer.name if inv.job and inv.job.customer else "Unknown"
        ))
    
    # Fix total amount from Job
    for i, inv in enumerate(invoices):
         if inv.job and inv.job.value:
             output[i].total_amount = inv.job.value

    return output

@router.get("/{invoice_id}", response_model=InvoiceSchema)
async def get_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_db)
):
    from src.models import Job
    query = (
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.job).selectinload(Job.customer))
    )
    result = await session.execute(query)
    inv = result.scalar_one_or_none()
    
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return InvoiceSchema(
        id=inv.id,
        job_id=inv.job_id,
        total_amount=inv.job.value if inv.job and inv.job.value else 0.0,
        status=inv.status,
        created_at=inv.created_at,
        public_url=inv.public_url,
        customer_name=inv.job.customer.name if inv.job and inv.job.customer else "Unknown"
    )
