import asyncio
import pytest
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, User, UserRole, InvoicingWorkflow, Job
from src.services.workflow import WorkflowSettingsService
from src.services.template_service import TemplateService
from src.uimodels import GetWorkflowSettingsTool, UpdateWorkflowSettingsTool
from src.tool_executor import ToolExecutor
from src.services.rbac_service import RBACService

# Use a separate test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def setup_db():
    RBACService._config = None  # Force reload of RBAC config
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.mark.asyncio
async def test_workflow_settings_defaults():
    await setup_db()
    async with TestAsyncSessionLocal() as session:
        business = Business(
            name="Test Workflow Biz",
            subscription_status="free",
            seat_limit=1,
            active_addons=[],
            quickbooks_connected=False
        )
        session.add(business)
        await session.commit()
        
        service = WorkflowSettingsService(session)
        settings = await service.get_settings(business.id)
        
        assert settings["workflow_invoicing"] == InvoicingWorkflow.MANUAL
        assert settings["workflow_tax_inclusive"] is True
        print("test_workflow_settings_defaults passed!")

@pytest.mark.asyncio
async def test_workflow_tool_rbac():
    await setup_db()
    async with TestAsyncSessionLocal() as session:
        business = Business(
            name="RBAC Biz",
            subscription_status="free",
            seat_limit=2,
            active_addons=[],
            quickbooks_connected=False
        )
        session.add(business)
        await session.flush()
        
        owner = User(name="Owner", business_id=business.id, role=UserRole.OWNER, phone_number="123")
        employee = User(name="Employee", business_id=business.id, role=UserRole.EMPLOYEE, phone_number="456")
        session.add_all([owner, employee])
        await session.commit()
        
        template_service = MagicMock(spec=TemplateService)
        
        # Test as Owner
        executor_owner = ToolExecutor(session, business.id, owner.id, owner.phone_number, template_service)
        tool = UpdateWorkflowSettingsTool(invoicing="automatic")
        msg, _ = await executor_owner.execute(tool)
        assert "successfully" in msg.lower()
        
        # Verify change
        service = WorkflowSettingsService(session)
        settings = await service.get_settings(business.id)
        assert settings["workflow_invoicing"] == InvoicingWorkflow.AUTOMATIC
        
        # Test as Employee
        executor_emp = ToolExecutor(session, business.id, employee.id, employee.phone_number, template_service)
        tool2 = UpdateWorkflowSettingsTool(invoicing="never")
        msg, _ = await executor_emp.execute(tool2)
        assert "don't have permission" in msg.lower()
        
        # Verify NO change
        settings = await service.get_settings(business.id)
        assert settings["workflow_invoicing"] == InvoicingWorkflow.AUTOMATIC
        print("test_workflow_tool_rbac passed!")

@pytest.mark.asyncio
async def test_workflow_tool_validation():
    await setup_db()
    async with TestAsyncSessionLocal() as session:
        business = Business(name="Val Biz", subscription_status="free", active_addons=[])
        session.add(business)
        await session.flush()
        owner = User(name="Owner", business_id=business.id, role=UserRole.OWNER, phone_number="789")
        session.add(owner)
        await session.commit()
        
        template_service = MagicMock(spec=TemplateService)
        executor = ToolExecutor(session, business.id, owner.id, owner.phone_number, template_service)
        
        # Invalid enum value
        tool = UpdateWorkflowSettingsTool(invoicing="invalid_value")
        msg, _ = await executor.execute(tool)
        assert "error" in msg.lower()
        assert "invalid invoicing value" in msg.lower()
        
        # Get settings tool
        tool_get = GetWorkflowSettingsTool()
        msg, data = await executor.execute(tool_get)
        assert "Current Workflow Settings" in msg
        assert data["settings"]["workflow_invoicing"] == InvoicingWorkflow.MANUAL
        print("test_workflow_tool_validation passed!")
        
    @pytest.mark.asyncio
    async def test_workflow_job_creation_default():
        await setup_db()
        async with TestAsyncSessionLocal() as session:
            business = Business(name="Job Default Biz", subscription_status="free", active_addons=[])
            session.add(business)
            await session.flush()
            
            owner = User(name="Owner", business_id=business.id, role=UserRole.OWNER, phone_number="999")
            session.add(owner)
            await session.commit()
            
            template_service = MagicMock(spec=TemplateService)
            template_service.render.return_value = "Mocked Response"
            
            # Helper to create/execute tool
            async def execute_add_job(settings_value=None):
                # Update setting
                if settings_value:
                    # Update directly in DB for speed
                    await session.execute(
                         sa.update(Business)
                         .where(Business.id == business.id)
                         .values(workflow_job_creation_default=settings_value)
                    )
                    await session.commit()

                executor = ToolExecutor(session, business.id, owner.id, owner.phone_number, template_service)
                # Ensure customer exists (mocked or pre-created)
                # Actually AddJobTool creates customer if not exists, so it's fine.
                
                tool = AddJobTool(customer_name="Test Customer", price=100)
                msg, data = await executor.execute(tool)
                return data

            import sqlalchemy as sa
            from src.uimodels import AddJobTool
            from src.models import JobCreationDefault

            # 1. Default (None or UNSCHEDULED) -> Pending
            data = await execute_add_job()
            assert data["action"] == "create"
            # Retrieve job to check status
            job = await session.get(Job, data["id"])
            assert job.status == JobStatus.PENDING

            # 2. MARK_DONE -> Done
            data = await execute_add_job(JobCreationDefault.MARK_DONE)
            job = await session.get(Job, data["id"])
            assert job.status == "done"

            # 3. AUTO_SCHEDULE -> Pending (for now)
            data = await execute_add_job(JobCreationDefault.AUTO_SCHEDULE)
            job = await session.get(Job, data["id"])
            assert job.status == JobStatus.PENDING
            
            print("test_workflow_job_creation_default passed!")

if __name__ == "__main__":
    async def run_all():
        try:
            await test_workflow_settings_defaults()
            await test_workflow_tool_rbac()
            await test_workflow_tool_validation()
            await test_workflow_job_creation_default()
            print("\nALL TESTS PASSED")
        except Exception as e:
            print(f"\nTESTS FAILED: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(run_all())