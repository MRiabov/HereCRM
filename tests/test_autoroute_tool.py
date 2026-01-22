import pytest
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Job, Customer, Business
from src.tools.routing_tools import AutorouteToolExecutor
from src.uimodels import AutorouteTool

@pytest.mark.asyncio
async def test_autoroute_preview_basic(async_session: AsyncSession):
    # 1. Setup Data
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    
    business_id = business.id
    
    # Employees
    emp1 = User(name="Alice", business_id=business_id, 
                default_start_location_lat=52.5200, default_start_location_lng=13.4050)
    emp2 = User(name="Bob", business_id=business_id,
                default_start_location_lat=52.5200, default_start_location_lng=13.4050)
    async_session.add_all([emp1, emp2])
    
    # Customers
    c1 = Customer(name="Customer 1", business_id=business_id, latitude=52.5300, longitude=13.4150)
    c2 = Customer(name="Customer 2", business_id=business_id, latitude=52.5400, longitude=13.4250)
    async_session.add_all([c1, c2])
    await async_session.commit()
    
    # Jobs
    # One scheduled for today, unassigned
    j1 = Job(business_id=business_id, customer_id=c1.id, description="Job 1", 
             status="scheduled", scheduled_at=datetime.combine(date.today(), datetime.min.time()),
             latitude=c1.latitude, longitude=c1.longitude)
    # One pending
    j2 = Job(business_id=business_id, customer_id=c2.id, description="Job 2", 
             status="pending",
             latitude=c2.latitude, longitude=c2.longitude)
    async_session.add_all([j1, j2])
    await async_session.commit()
    
    # 2. Run Tool
    executor = AutorouteToolExecutor(async_session, business_id)
    tool_input = AutorouteTool(date=date.today().isoformat())
    
    report = await executor.run(tool_input)
    
    # 3. Assertions
    assert "Proposed Schedule" in report
    assert "Alice" in report or "Bob" in report
    assert "Customer 1" in report
    assert "Customer 2" in report

@pytest.mark.asyncio
async def test_autoroute_no_jobs(async_session: AsyncSession):
    business = Business(name="Empty Biz")
    async_session.add(business)
    await async_session.commit()
    
    # Add employee
    emp = User(name="Alice", business_id=business.id)
    async_session.add(emp)
    await async_session.commit()
    
    executor = AutorouteToolExecutor(async_session, business.id)
    tool_input = AutorouteTool(date=date.today().isoformat())
    
    report = await executor.run(tool_input)
    
    assert "No jobs found to route" in report
