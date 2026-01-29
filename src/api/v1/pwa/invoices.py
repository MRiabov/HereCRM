from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Invoice, Job, Customer, User
from src.schemas.pwa import InvoiceSchema, InvoiceCreate
from src.api.dependencies.clerk_auth import get_current_user
from src.services.invoice_service import InvoiceService

router = APIRouter()

@router.post("/", response_model=InvoiceSchema)
async def create_invoice(
    invoice_data: InvoiceCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify job belongs to business
    stmt = select(Job).where(Job.id == invoice_data.job_id, Job.business_id == current_user.business_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    invoice_service = InvoiceService(session)
    try:
        invoice = await invoice_service.create_invoice(
            job, 
            force_regenerate=invoice_data.force_regenerate,
            invoice_number=invoice_data.invoice_number,
            issued_at=invoice_data.issued_at,
            due_date=invoice_data.due_date,
            notes=invoice_data.notes,
            items=[item.model_dump() for item in invoice_data.items] if invoice_data.items else None
        )
        await session.commit()
        
        return InvoiceSchema(
            id=invoice.id,
            job_id=invoice.job_id,
            invoice_number=f"INV-{invoice.id:03d}", # Added
            total_amount=job.value or 0.0,
            status=invoice.status,
            created_at=invoice.created_at,
            public_url=invoice.public_url,
            customer_name=job.customer.name if job and job.customer else "Unknown"
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[InvoiceSchema])
async def list_invoices(
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve invoices with Job and Customer info
    stmt = (
        select(Invoice)
        .join(Invoice.job)
        .join(Job.customer)
        .where(Job.business_id == current_user.business_id)
        .options(
            joinedload(Invoice.job).joinedload(Job.customer)
        )
    )

    ignore_keywords = ["all", "invoices", "show invoices", "show all invoices", "list invoices"]
    if search and search.strip().lower() not in ignore_keywords:
        # Search by Invoice ID (if numeric), Customer Name, or Job Description
        search_filters: List[Any] = [
            Customer.name.ilike(f"%{search}%"),
            Job.description.ilike(f"%{search}%")
        ]
        if search.isdigit():
            search_filters.append(Invoice.id == int(search))
        
        stmt = stmt.where(or_(*search_filters))

    stmt = stmt.order_by(desc(Invoice.created_at))
    
    result = await session.execute(stmt)
    invoices = result.scalars().unique().all()

    response = []
    for inv in invoices:
        # Populate schema fields
        # InvoiceSchema needs: id, job_id, total_amount, status, created_at, public_url, customer_name
        response.append(InvoiceSchema(
            id=inv.id,
            job_id=inv.job_id,
            invoice_number=f"INV-{inv.id:03d}", # Added
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
        invoice_number=f"INV-{invoice.id:03d}", # Added
        total_amount=invoice.job.value or 0.0,
        status=invoice.status,
        created_at=invoice.created_at,
        public_url=invoice.public_url,
        customer_name=invoice.job.customer.name if invoice.job and invoice.job.customer else "Unknown"
    )
