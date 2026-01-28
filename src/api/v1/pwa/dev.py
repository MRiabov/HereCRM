from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db, engine
from src.models import Base
from src.config import settings
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, UserRole, Business, Customer, Job, Service, LineItem, Expense, PipelineStage, JobStatus
from datetime import datetime, timedelta, timezone
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def populate_demo_data(db: AsyncSession):
    # 1. Create a Demo Business
    business = Business(
        name="Demo Home Services",
        default_city="Dublin",
        default_country="Ireland",
        workflow_tax_inclusive=True,
        active_addons=["manage_employees", "campaigns"]
    )
    db.add(business)
    await db.flush()

    # 2. Create Users
    owner = User(
        clerk_id="user_demo_owner",
        name="Demo Owner",
        email="owner@demo.com",
        phone_number="+353871111111",
        business_id=business.id,
        role=UserRole.OWNER
    )
    tech = User(
        clerk_id="user_demo_tech",
        name="John Technician",
        email="john@demo.com",
        phone_number="+353872222222",
        business_id=business.id,
        role=UserRole.EMPLOYEE
    )
    db.add_all([owner, tech])
    await db.flush()

    # 3. Create Service Catalog
    services = [
        Service(business_id=business.id, name="Window Cleaning", default_price=50.0, estimated_duration=60),
        Service(business_id=business.id, name="Gutter Repair", default_price=120.0, estimated_duration=90),
        Service(business_id=business.id, name="Power Washing", default_price=200.0, estimated_duration=120),
    ]
    db.add_all(services)
    await db.flush()

    # 4. Create Customers
    customers = [
        Customer(business_id=business.id, name="Alice Jones", phone="+353873333333", email="alice@example.com", street="123 O'Connell St", city="Dublin", pipeline_stage=PipelineStage.CONVERTED_RECURRENT),
        Customer(business_id=business.id, name="Bob Smith", phone="+353874444444", email="bob@example.com", street="45 Grafton St", city="Dublin", pipeline_stage=PipelineStage.CONTACTED),
        Customer(business_id=business.id, name="Charlie Brown", phone="+353875555555", email="charlie@example.com", street="10 Temple Bar", city="Dublin", pipeline_stage=PipelineStage.NOT_CONTACTED),
    ]
    db.add_all(customers)
    await db.flush()

    # 5. Create Jobs
    # Completed Job
    job1 = Job(
        business_id=business.id,
        customer_id=customers[0].id,
        description="Full house window cleaning",
        status=JobStatus.COMPLETED,
        value=50.0,
        location="123 O'Connell St",
        employee_id=tech.id,
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=2),
        paid=True
    )
    # Scheduled Job
    job2 = Job(
        business_id=business.id,
        customer_id=customers[1].id,
        description="Gutter repair",
        status=JobStatus.SCHEDULED,
        value=120.0,
        location="45 Grafton St",
        employee_id=tech.id,
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1, hours=2)
    )
    db.add_all([job1, job2])
    await db.flush()

    # 6. Line Items
    li1 = LineItem(job_id=job1.id, service_id=services[0].id, description="Window Cleaning", quantity=1, unit_price=50.0, total_price=50.0)
    li2 = LineItem(job_id=job2.id, service_id=services[1].id, description="Gutter Repair", quantity=1, unit_price=120.0, total_price=120.0)
    db.add_all([li1, li2])

    # 7. Expenses
    exp1 = Expense(
        business_id=business.id,
        employee_id=tech.id,
        amount=25.50,
        category="Fuel",
        description="Diesel for van",
        created_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db.add(exp1)

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
