from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db, engine
from src.models import Base
from src.config import settings
from src.api.dependencies.clerk_auth import get_current_user
from src.models import (
    User, UserRole, Business, Customer, Job, Service, LineItem, Expense, 
    PipelineStage, JobStatus, Invoice, InvoiceStatus, Quote, QuoteStatus, 
    QuoteLineItem, Request as CRMRequest, RequestStatus, Urgency, WageConfiguration, 
    WageModelType, LedgerEntry, LedgerEntryType, ExpenseCategory,
    Campaign, CampaignRecipient, CampaignStatus, CampaignChannel, RecipientStatus,
    WhatsAppTemplate, WhatsAppTemplateStatus, WhatsAppTemplateCategory,
    ImportJob, ImportStatus, ExportRequest, ExportStatus, ExportFormat,
    Invitation, InvitationStatus, Message, MessageRole, MessageType,
    MessageStatus, MessageLog, MessageTriggerSource, Payment, PaymentMethod,
    PaymentStatus, SyncLog, SyncType, SyncLogStatus, ConversationStatus,
    ConversationState
)
from datetime import datetime, timedelta, timezone
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

async def populate_demo_data(db: AsyncSession):
    # 1. Create a Demo Business
    business = Business(
        name="Demo Home Services",
        default_city="Dublin",
        default_country="Ireland",
        workflow_tax_inclusive=True,
        default_tax_rate=8.25,
        active_addons=["manage_employees", "campaigns"]
    )
    db.add(business)
    await db.flush()

    # 2. Create Users
    # Use the actual clerk ID from E2E tests if available, otherwise fallback
    owner_clerk_id = "user_38td2lMr5JN9ZvyReFkzCKh6E2B" 
    
    owner = User(
        clerk_id=owner_clerk_id,
        name="Demo Owner",
        email="debug+clerk_test@example.com",
        phone_number="+353871111111",
        business_id=business.id,
        role=UserRole.OWNER
    )
    # Technician 1
    tech1 = User(
        clerk_id="user_tech1",
        name="Tech One",
        email="tech1@example.com",
        phone_number="+353872222222",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    # Technician 2
    tech2 = User(
        clerk_id="user_tech2",
        name="Tech Two",
        email="tech2@example.com",
        phone_number="+353873333333",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    # Staff / Manager
    staff = User(
        clerk_id="user_staff",
        name="Office Staff",
        email="staff@example.com",
        phone_number="+353870000000",
        business_id=business.id,
        role=UserRole.MANAGER
    )
    db.add_all([owner, tech1, tech2, staff])
    await db.flush()

    # 3. Create Services
    services = [
        Service(business_id=business.id, name="Window Cleaning", description="Exterior and interior window cleaning", default_price=120.0),
        Service(business_id=business.id, name="Gutter Cleaning", description="Clear debris from gutters", default_price=80.0),
        Service(business_id=business.id, name="Fix Leak", description="Standard plumbing repair", default_price=150.0),
    ]
    db.add_all(services)
    await db.flush()

    # 4. Create Customers
    customers = [
        Customer(business_id=business.id, name="John Doe", phone="+353871234567", email="john@example.com", street="123 Main St", city="Dublin", pipeline_stage=PipelineStage.CONTACTED),
        Customer(business_id=business.id, name="Jane Smith", phone="+353871234569", email="jane@example.com", street="45 Grafton St", city="Dublin", pipeline_stage=PipelineStage.QUOTED),
        Customer(business_id=business.id, name="Alice Wonderland", phone="+353871111112", email="alice@example.com", street="123 O'Connell St", city="Dublin", pipeline_stage=PipelineStage.CONTACTED),
        Customer(business_id=business.id, name="Bob Builder", phone="+353874444444", email="bob@example.com", street="78 Wall St", city="Dublin", pipeline_stage=PipelineStage.NOT_CONTACTED),
        Customer(business_id=business.id, name="Charlie Brown", phone="+353875555555", email="charlie@example.com", street="10 Temple Bar", city="Dublin", pipeline_stage=PipelineStage.NOT_CONTACTED),
        Customer(business_id=business.id, name="John Smith", phone="+353871234568", email="john.smith@example.com", street="124 Main St", city="Dublin", pipeline_stage=PipelineStage.CONTACTED),
        Customer(business_id=business.id, name="Test Customer", phone="+353879999999", email="test@example.com", street="99 Test Rd", city="Dublin", pipeline_stage=PipelineStage.NOT_CONTACTED),
    ]
    db.add_all(customers)
    await db.flush()

    # 5. Create Jobs
    # Completed Job for John Doe
    job1 = Job(
        business_id=business.id,
        customer_id=customers[0].id,
        description="Fix leaking tap",
        status=JobStatus.COMPLETED,
        value=150.0,
        location="123 Main St",
        employee_id=tech1.id,
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=2),
        paid=True
    )
    # Scheduled Job for Jane Smith
    job2 = Job(
        business_id=business.id,
        customer_id=customers[1].id,
        description="Morning Repair",
        status=JobStatus.SCHEDULED,
        value=120.0,
        location="45 Grafton St",
        employee_id=tech1.id,
        scheduled_at=datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    )
    # Another scheduled job
    job3 = Job(
        business_id=business.id,
        customer_id=customers[2].id,
        description="Afternoon Install",
        status=JobStatus.SCHEDULED,
        value=300.0,
        location="123 O'Connell St",
        employee_id=tech2.id,
        scheduled_at=datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
    )
    # Job for search tests
    job4 = Job(
        business_id=business.id,
        customer_id=customers[5].id,
        description="John Boiler Repair",
        status=JobStatus.PENDING,
        value=500.0,
        location="124 Main St",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=3)
    )
    # "Test Job" for search tests
    job5 = Job(
        business_id=business.id,
        customer_id=customers[6].id,
        description="Test Job",
        status=JobStatus.PENDING,
        value=100.0,
        location="99 Test Rd",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=4)
    )
    # "Fix Leak" and "AC Service" for inline job search
    job6 = Job(
        business_id=business.id,
        customer_id=customers[4].id,
        description="Fix Leak",
        status=JobStatus.COMPLETED,
        value=150.0,
        location="10 Temple Bar",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    job7 = Job(
        business_id=business.id,
        customer_id=customers[4].id,
        description="AC Service",
        status=JobStatus.SCHEDULED,
        value=200.0,
        location="10 Temple Bar",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2)
    )

    db.add_all([job1, job2, job3, job4, job5, job6, job7])
    await db.flush()

    # 6. Line Items
    li1 = LineItem(job_id=job1.id, service_id=services[2].id, description="Fix leaking tap", quantity=1, unit_price=150.0, total_price=150.0)
    li2 = LineItem(job_id=job2.id, service_id=services[0].id, description="Morning Repair", quantity=1, unit_price=120.0, total_price=120.0)
    db.add_all([li1, li2])
    await db.flush()

    # 7. Invoices & Quotes
    invoice1 = Invoice(
        job_id=job1.id,
        s3_key="invoices/inv-001.pdf",
        public_url="https://demo.herecrm.com/inv-001.pdf",
        status=InvoiceStatus.PAID,
        created_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    
    quote1 = Quote(
        customer_id=customers[1].id,
        business_id=business.id,
        status=QuoteStatus.SENT,
        total_amount=500.0,
        subtotal=500.0,
        tax_amount=0.0,
        tax_rate=0.0,
        title="Standard Maintenance",
        external_token=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc) - timedelta(days=3)
    )
    db.add_all([invoice1, quote1])
    await db.flush()

    qli1 = QuoteLineItem(quote_id=quote1.id, service_id=services[1].id, description="Boiler Repair", quantity=2, unit_price=250.0, total=500.0)
    db.add(qli1)

    # 8. Expenses
    exp1 = Expense(
        business_id=business.id,
        employee_id=tech1.id,
        amount=25.50,
        category=ExpenseCategory.FUEL,
        description="Diesel for van",
        created_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db.add(exp1)

    # 9. Requests
    req1 = CRMRequest(
        business_id=business.id,
        customer_id=customers[0].id,
        description="Leaking pipe in kitchen",
        status=RequestStatus.PENDING,
        urgency=Urgency.HIGH,
        created_at=datetime.now(timezone.utc) - timedelta(hours=5)
    )
    db.add(req1)

    # 10. Wage Configurations & Ledger Entries
    wc_staff = WageConfiguration(
        user_id=staff.id,
        model_type=WageModelType.HOURLY_PER_JOB,
        rate_value=25.0,
        tax_withholding_rate=15.0,
        allow_expense_claims=True
    )
    db.add(wc_staff)
    await db.flush()

    le1 = LedgerEntry(
        employee_id=staff.id,
        amount=1250.0,
        entry_type=LedgerEntryType.WAGE,
        description="Weekly wage",
        created_at=datetime.now(timezone.utc) - timedelta(days=7)
    )
    db.add(le1)

    # 11. Messages
    msg1 = Message(
        business_id=business.id,
        user_id=owner.id,
        from_number="+353871111111",
        to_number=customers[0].phone,
        body="Hi John, your job is scheduled for tomorrow at 10 AM.",
        role=MessageRole.ASSISTANT,
        channel_type=MessageType.WHATSAPP,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2)
    )
    msg2 = Message(
        business_id=business.id,
        user_id=None,
        from_number=customers[0].phone,
        to_number="+353871111111",
        body="Great, thank you!",
        role=MessageRole.USER,
        channel_type=MessageType.WHATSAPP,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db.add_all([msg1, msg2])

    await db.commit()

@router.post("/reset-db")
async def reset_db(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not settings.dev_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation is only allowed in DEV_MODE."
        )
    
    # Only allow owners to do this even in dev mode
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can reset the database."
        )

    logger.info("Resetting database and populating demo data...")
    
    try:
        # Drop and Recreate
        async with engine.begin() as conn:
            # We must be careful here. If we use SQLite, we can drop all.
            # But we must ensure the models are imported.
            # Base.metadata.drop_all/create_all is sync by default but engine.run_sync can handle it.
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        # Re-populate
        await populate_demo_data(db)
        
        return {"status": "SUCCESS", "message": "Database reset and demo data populated. You might need to sign in again if your user was deleted (but demo users were created)."}
    except Exception as e:
        logger.exception("Database reset failed")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@router.get("/errors")
async def get_backend_errors(request: Request):
    if not settings.dev_mode:
        raise HTTPException(status_code=403, detail="Only in dev mode")
    errors = getattr(request.app.state, "backend_errors", [])
    return {"errors": errors}

@router.delete("/errors")
async def clear_backend_errors(request: Request):
    if not settings.dev_mode:
        raise HTTPException(status_code=403, detail="Only in dev mode")
    request.app.state.backend_errors = []
    return {"status": "SUCCESS"}
