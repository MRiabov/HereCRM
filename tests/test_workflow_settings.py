import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, InvoicingWorkflow, QuotingWorkflow, PaymentTiming
from src.services.workflow import WorkflowSettingsService
from sqlalchemy import select

# Use a separate test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def test_workflow_settings_defaults():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestAsyncSessionLocal() as session:
        # Create a business without setting workflow fields
        business = Business(
            name="Test Workflow Biz",
            subscription_status="free",
            seat_limit=1,
            active_addons=["manage_employees"],
            quickbooks_connected=False
        )
        session.add(business)
        await session.commit()
        
        service = WorkflowSettingsService(session)
        settings = await service.get_settings(business.id)
        
        assert settings["workflow_invoicing"] == InvoicingWorkflow.MANUAL
        assert settings["workflow_quoting"] == QuotingWorkflow.MANUAL
        assert settings["workflow_payment_timing"] == PaymentTiming.USUALLY_PAID_ON_SPOT
        assert settings["workflow_tax_inclusive"] is True
        assert settings["workflow_include_payment_terms"] is False
        assert settings["workflow_enable_reminders"] is False
        print("test_workflow_settings_defaults passed!")

async def test_workflow_settings_update():
    async with TestAsyncSessionLocal() as session:
        # Get the business
        stmt = select(Business).where(Business.name == "Test Workflow Biz")
        result = await session.execute(stmt)
        business = result.scalar_one()
        
        service = WorkflowSettingsService(session)
        await service.update_settings(
            business.id,
            workflow_invoicing=InvoicingWorkflow.AUTOMATIC,
            workflow_tax_inclusive=False
        )
        await session.commit()
        
        # Fresh read
        settings = await service.get_settings(business.id)
        assert settings["workflow_invoicing"] == InvoicingWorkflow.AUTOMATIC
        assert settings["workflow_tax_inclusive"] is False
        # Others should still be default
        assert settings["workflow_quoting"] == QuotingWorkflow.MANUAL
        print("test_workflow_settings_update passed!")

if __name__ == "__main__":
    async def run_all():
        await test_workflow_settings_defaults()
        await test_workflow_settings_update()

    asyncio.run(run_all())