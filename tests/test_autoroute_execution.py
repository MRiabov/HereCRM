import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Job, Customer, Business
from src.tools.routing_tools import AutorouteToolExecutor
from src.uimodels import AutorouteTool

@pytest.mark.asyncio
async def test_autoroute_apply_execution(async_session: AsyncSession):
    # 1. Setup Data
    business = Business(name="Apply Test Biz")
    async_session.add(business)
    await async_session.commit()
    
    business_id = business.id
    
    # Employees
    emp1 = User(name="Alice", business_id=business_id, phone_number="1234567890",
                default_start_location_lat=52.52, default_start_location_lng=13.40)
    async_session.add(emp1)
    
    # Customers
    c1 = Customer(name="Customer 1", business_id=business_id, phone="9876543210", latitude=52.53, longitude=13.41)
    async_session.add(c1)
    await async_session.commit()
    
    # Jobs - Pending
    j1 = Job(business_id=business_id, customer_id=c1.id, description="Job Apply 1", 
             status="pending", latitude=c1.latitude, longitude=c1.longitude)
    async_session.add(j1)
    await async_session.commit()
    
    # Verify initial state
    assert j1.employee_id is None
    assert j1.status == "pending"

    # 2. Run Tool with apply=True
    # We patch messaging service to avoid actual queuing/side effects and check calls
    with patch("src.tools.routing_tools.messaging_service") as mock_msg_service:
        mock_msg_service.enqueue_message = AsyncMock()
        
        mock_ts = MagicMock()
        mock_ts.render.return_value = "Successfully applied schedule"
        executor = AutorouteToolExecutor(async_session, business_id, mock_ts)
        # Force mock routing service to return a specific predictable solution?
        # The MockRoutingService used by default (if no API key) basically checks distance.
        # With 1 job and 1 employee nearby, it should assign it.
        
        tool_input = AutorouteTool(date=date.today().isoformat(), apply=True, notify=True)
        
        report = await executor.run(tool_input)
        
        assert "Successfully applied schedule" in report
        
        # 3. Verify DB Changes
        await async_session.refresh(j1)
        assert j1.employee_id == emp1.id
        assert j1.status == "scheduled"
        assert j1.scheduled_at is not None
        
        # 4. Verify Notifications
        # Should notify employee
        # Customer notification logic in routing_tools.py is currently just a logger.info, 
        # but employee notification uses messaging_service
        
        assert mock_msg_service.enqueue_message.called
        # Check call args
        call_args = mock_msg_service.enqueue_message.call_args_list[0]
        assert call_args.kwargs['recipient_phone'] == "1234567890"
        assert "New job assigned" in call_args.kwargs['content']

@pytest.mark.asyncio
async def test_autoroute_apply_rollback_on_error(async_session: AsyncSession):
    # Setup similar data
    business = Business(name="Rollback Biz")
    async_session.add(business)
    await async_session.commit()
    
    bid = business.id
    emp = User(name="Bob", business_id=bid, default_start_location_lat=52.52, default_start_location_lng=13.40)
    c = Customer(name="Cust", business_id=bid, latitude=52.53, longitude=13.41)
    async_session.add_all([emp, c])
    await async_session.commit()
    
    j = Job(business_id=bid, customer_id=c.id, description="Job Rollback", status="pending", latitude=52.53, longitude=13.41)
    async_session.add(j)
    await async_session.commit()

    # Patch commit to fail
    with patch("src.tools.routing_tools.messaging_service") as m:
        # We need to simulate a failure during apply_schedule
        # Ideally we'd mock the session.commit() but that's on self.session which is the async_session provided by pytest
        # Instead, let's mock user_repo or similar to raise an exception halfway
        
        mock_ts = MagicMock()
        executor = AutorouteToolExecutor(async_session, bid, mock_ts)
        
        # Mocking user_repo.get_by_id to raise exception
        executor.user_repo.get_by_id = AsyncMock(side_effect=Exception("Database Boom"))
        
        tool_input = AutorouteTool(date=date.today().isoformat(), apply=True)
        
        report = await executor.run(tool_input)
        
        assert "Failed to apply schedule" in report
        assert "Database Boom" in report
        
        # Verify Job is NOT updated (rollback happened)
        # Note: In a real DB with transaction, rollback restores state. 
        # With pytest-asyncio and sqlite memory, it should work if session is handled right.
        await async_session.refresh(j)
        assert j.employee_id is None
        assert j.status == "pending"
