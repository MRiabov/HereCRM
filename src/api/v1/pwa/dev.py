from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db, engine
from src.models import Base
from src.config import settings
from src.api.dependencies.clerk_auth import get_current_user
from src.models import (
    User,
    UserRole,
    Business,
    Customer,
    Job,
    Service,
    LineItem,
    Expense,
    PipelineStage,
    JobStatus,
    Invoice,
    InvoiceStatus,
    Quote,
    QuoteStatus,
    QuoteLineItem,
    Request as CRMRequest,
    RequestStatus,
    Urgency,
    WageConfiguration,
    WageModelType,
    LedgerEntry,
    LedgerEntryType,
    ExpenseCategory,
    Message,
    MessageRole,
    MessageType,
)
from datetime import datetime, timedelta, timezone
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)


async def populate_demo_data(db: AsyncSession, owner_clerk_id: str):
    # 1. Create a Demo Business
    business = Business(
        name="Apex Home Maintenance",
        default_city="Metro City",
        default_country="United States",
        workflow_tax_inclusive=False,
        default_tax_rate=8.0,
        active_addons=["manage_employees", "campaigns"],
    )
    db.add(business)
    await db.flush()

    # 2. Create Users
    owner = User(
        clerk_id=owner_clerk_id,
        name="Patrick Sanders",
        email="patrick.sanders@apexmaintenance.com",
        phone_number="+15550101111",
        business_id=business.id,
        role=UserRole.OWNER,
    )
    # Technician 1
    tech1 = User(
        clerk_id="user_tech1",
        name="Kevin Turner",
        email="kevin.turner@apexmaintenance.com",
        phone_number="+15550102222",
        business_id=business.id,
        role=UserRole.EMPLOYEE,
    )
    # Technician 2
    tech2 = User(
        clerk_id="user_tech2",
        name="Daniel Bennett",
        email="daniel.bennett@apexmaintenance.com",
        phone_number="+15550103333",
        business_id=business.id,
        role=UserRole.EMPLOYEE,
    )
    # Staff / Manager
    staff = User(
        clerk_id="user_staff",
        name="Sarah Jenkins",
        email="sarah.jenkins@apexmaintenance.com",
        phone_number="+15550104444",
        business_id=business.id,
        role=UserRole.MANAGER,
    )
    db.add_all([owner, tech1, tech2, staff])
    await db.flush()

    # 3. Create Services
    services = [
        Service(
            business_id=business.id,
            name="Window Cleaning & Treatment",
            description="Exterior and interior window cleaning including frames",
            default_price=120.0,
        ),
        Service(
            business_id=business.id,
            name="Gutter Cleaning & Repair",
            description="Clear debris and fix minor leaks",
            default_price=80.0,
        ),
        Service(
            business_id=business.id,
            name="Plumbing Repair",
            description="Standard plumbing diagnostics and repair",
            default_price=150.0,
        ),
    ]
    db.add_all(services)
    await db.flush()

    # 4. Create Customers
    customers = [
        Customer(
            business_id=business.id,
            name="Michael Gordon",
            first_name="Michael",
            last_name="Gordon",
            phone="+15551234567",
            email="m.gordon@gmail.com",
            street="14 Oakwood Avenue",
            city="Metro City",
            pipeline_stage=PipelineStage.CONTACTED,
        ),
        Customer(
            business_id=business.id,
            name="Sarah Peterson",
            first_name="Sarah",
            last_name="Peterson",
            phone="+15551234569",
            email="sarah.peterson@outlook.com",
            street="22 Marina Village",
            city="Metro City",
            pipeline_stage=PipelineStage.QUOTED,
        ),
        Customer(
            business_id=business.id,
            name="Nicole Kennedy",
            first_name="Nicole",
            last_name="Kennedy",
            phone="+15551111112",
            email="nicole.k@example.com",
            street="5 Seafield Road",
            city="Metro City",
            pipeline_stage=PipelineStage.CONTACTED,
        ),
        Customer(
            business_id=business.id,
            name="Christopher Evans",
            first_name="Christopher",
            last_name="Evans",
            phone="+15554444444",
            email="chris.evans@gmail.com",
            street="88 Merrion Square",
            city="Metro City",
            pipeline_stage=PipelineStage.NOT_CONTACTED,
        ),
        Customer(
            business_id=business.id,
            name="Luke Roberts",
            first_name="Luke",
            last_name="Roberts",
            phone="+15555555555",
            email="luke.roberts@hotmail.com",
            street="12 Harcourt Street",
            city="Metro City",
            pipeline_stage=PipelineStage.NOT_CONTACTED,
        ),
        Customer(
            business_id=business.id,
            name="Eric Wallace",
            first_name="Eric",
            last_name="Wallace",
            phone="+15551234568",
            email="eric.wallace@gmail.com",
            street="34 Collins Avenue",
            city="Metro City",
            pipeline_stage=PipelineStage.CONTACTED,
        ),
        Customer(
            business_id=business.id,
            name="Fiona Barnes",
            first_name="Fiona",
            last_name="Barnes",
            phone="+15559999999",
            email="fiona.barnes@test.com",
            street="7 Park Avenue",
            city="Metro City",
            pipeline_stage=PipelineStage.NOT_CONTACTED,
        ),
    ]
    db.add_all(customers)
    await db.flush()

    # 5. Create Jobs
    # Job for Michael Gordon
    job1 = Job(
        business_id=business.id,
        customer_id=customers[0].id,
        description="Kitchen Tap Replacement",
        status=JobStatus.COMPLETED,
        value=150.0,
        subtotal=132.16,
        tax_amount=17.84,
        tax_rate=13.5,
        location="14 Oakwood Avenue",
        employee_id=tech1.id,
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=2),
        paid=True,
    )
    # Scheduled Job for Sarah Peterson
    job2 = Job(
        business_id=business.id,
        customer_id=customers[1].id,
        description="Gutter Repair & Cleaning",
        status=JobStatus.SCHEDULED,
        value=120.0,
        subtotal=105.73,
        tax_amount=14.27,
        tax_rate=13.5,
        location="22 Marina Village",
        employee_id=tech1.id,
        scheduled_at=datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        + timedelta(days=1),
    )
    # Another scheduled job
    job3 = Job(
        business_id=business.id,
        customer_id=customers[2].id,
        description="New Radiator Installation",
        status=JobStatus.SCHEDULED,
        value=300.0,
        subtotal=264.32,
        tax_amount=35.68,
        tax_rate=13.5,
        location="5 Seafield Road",
        employee_id=tech2.id,
        scheduled_at=datetime.now(timezone.utc).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        + timedelta(days=1),
    )
    # Job for search tests
    job4 = Job(
        business_id=business.id,
        customer_id=customers[5].id,
        description="Boiler Service & Maintenance",
        status=JobStatus.PENDING,
        value=500.0,
        subtotal=440.53,
        tax_amount=59.47,
        tax_rate=13.5,
        location="34 Collins Avenue",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=3),
    )
    # "Test Job" for search tests
    job5 = Job(
        business_id=business.id,
        customer_id=customers[6].id,
        description="Emergency Leak Fix",
        status=JobStatus.PENDING,
        value=100.0,
        subtotal=88.11,
        tax_amount=11.89,
        tax_rate=13.5,
        location="7 Park Avenue",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=4),
    )
    # "Fix Leak" and "Heat Pump" for inline job search
    job6 = Job(
        business_id=business.id,
        customer_id=customers[4].id,
        description="Plumbing Repair",
        status=JobStatus.COMPLETED,
        value=150.0,
        subtotal=132.16,
        tax_amount=17.84,
        tax_rate=13.5,
        location="12 Harcourt Street",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    job7 = Job(
        business_id=business.id,
        customer_id=customers[4].id,
        description="Heat Pump Servicing",
        status=JobStatus.SCHEDULED,
        value=200.0,
        subtotal=176.21,
        tax_amount=23.79,
        tax_rate=13.5,
        location="12 Harcourt Street",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
    )

    db.add_all([job1, job2, job3, job4, job5, job6, job7])
    await db.flush()

    # 6. Line Items
    li1 = LineItem(
        job_id=job1.id,
        service_id=services[2].id,
        description="Kitchen Tap Replacement",
        quantity=1,
        unit_price=150.0,
        total_price=150.0,
    )
    li2 = LineItem(
        job_id=job2.id,
        service_id=services[0].id,
        description="Gutter Repair & Cleaning",
        quantity=1,
        unit_price=120.0,
        total_price=120.0,
    )
    db.add_all([li1, li2])
    await db.flush()

    # 7. Invoices & Quotes
    invoice1 = Invoice(
        job_id=job1.id,
        s3_key="invoices/inv-001.pdf",
        public_url="https://demo.herecrm.com/inv-001.pdf",
        status=InvoiceStatus.PAID,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    quote1 = Quote(
        customer_id=customers[1].id,
        business_id=business.id,
        status=QuoteStatus.SENT,
        total_amount=500.0,
        subtotal=440.53,
        tax_amount=59.47,
        tax_rate=13.5,
        title="Annual Maintenance Plan",
        external_token=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db.add_all([invoice1, quote1])
    await db.flush()

    qli1 = QuoteLineItem(
        quote_id=quote1.id,
        service_id=services[1].id,
        description="Boiler Service & Maintenance",
        quantity=2,
        unit_price=250.0,
        total=500.0,
    )
    db.add(qli1)

    # 8. Expenses
    exp1 = Expense(
        business_id=business.id,
        employee_id=tech1.id,
        amount=25.50,
        category=ExpenseCategory.FUEL,
        description="Diesel for van",
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(exp1)

    # 9. Requests
    req1 = CRMRequest(
        business_id=business.id,
        customer_id=customers[0].id,
        description="Burst pipe in kitchen under sink",
        status=RequestStatus.PENDING,
        urgency=Urgency.HIGH,
        subtotal=0,
        tax_amount=0,
        tax_rate=0,
        created_at=datetime.now(timezone.utc) - timedelta(hours=5),
    )
    db.add(req1)

    # 10. Wage Configurations & Ledger Entries
    wc_staff = WageConfiguration(
        user_id=staff.id,
        model_type=WageModelType.HOURLY_PER_JOB,
        rate_value=25.0,
        tax_withholding_rate=15.0,
        allow_expense_claims=True,
    )
    db.add(wc_staff)
    await db.flush()

    le1 = LedgerEntry(
        employee_id=staff.id,
        amount=1250.0,
        entry_type=LedgerEntryType.WAGE,
        description="Weekly wage",
        created_at=datetime.now(timezone.utc) - timedelta(days=7),
    )
    db.add(le1)

    # 11. Messages
    msg1 = Message(
        business_id=business.id,
        user_id=owner.id,
        from_number="+15550101111",
        to_number=customers[0].phone,
        body="Hi Michael, your appointment is confirmed for tomorrow at 10 AM.",
        role=MessageRole.ASSISTANT,
        channel_type=MessageType.WHATSAPP,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    msg2 = Message(
        business_id=business.id,
        user_id=None,
        from_number=customers[0].phone,
        to_number="+15550101111",
        body="Great, thank you!",
        role=MessageRole.USER,
        channel_type=MessageType.WHATSAPP,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.add_all([msg1, msg2])

    await db.commit()


@router.post("/reset-db")
async def reset_db(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if not settings.dev_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation is only allowed in DEV_MODE.",
        )

    # Only allow owners to do this even in dev mode
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can reset the database.",
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
        if not current_user.clerk_id:
            raise HTTPException(status_code=400, detail="Current user has no Clerk ID")
        await populate_demo_data(db, current_user.clerk_id)

        return {
            "status": "SUCCESS",
            "message": "Database reset and demo data populated. You might need to sign in again if your user was deleted (but demo users were created).",
        }
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
