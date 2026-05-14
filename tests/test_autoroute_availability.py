import pytest
from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Job, Customer, Business, JobStatus, CustomerAvailability
from src.tools.routing_tools import AutorouteToolExecutor
from src.uimodels import AutorouteTool

@pytest.mark.asyncio
async def test_autoroute_respects_availability(async_session: AsyncSession):
    # 1. Setup Data
    business = Business(name="Availability Test Biz")
    async_session.add(business)
    await async_session.commit()
    business_id = business.id

    # Employee starting at (0,0)
    emp1 = User(
        name="Alice",
        business_id=business_id,
        phone_number="1234567890",
        default_start_location_lat=0.0,
        default_start_location_lng=0.0,
    )
    async_session.add(emp1)

    # Customer at (0.1, 0.1) ~15km away
    c1 = Customer(
        name="Customer 1",
        business_id=business_id,
        phone="9876543210",
        latitude=0.1,
        longitude=0.1,
    )
    async_session.add(c1)
    await async_session.commit()

    # Availability: 14:00 - 16:00 on today's date
    today = date.today()
    start_time = datetime.combine(today, time(14, 0))
    end_time = datetime.combine(today, time(16, 0))

    availability = CustomerAvailability(
        customer_id=c1.id,
        start_time=start_time,
        end_time=end_time,
        is_available=True
    )
    async_session.add(availability)
    await async_session.commit()

    # Job
    j1 = Job(
        business_id=business_id,
        customer_id=c1.id,
        description="Job Availability 1",
        status=JobStatus.PENDING,
        latitude=c1.latitude,
        longitude=c1.longitude,
        estimated_duration=60
    )
    async_session.add(j1)
    await async_session.commit()

    # Verify job loading (optional debug step to confirm repo loads availability)
    from src.repositories import JobRepository
    job_repo = JobRepository(async_session)
    jobs = await job_repo.search(query="all", business_id=business_id, status=JobStatus.PENDING)
    assert len(jobs) == 1
    loaded_job = jobs[0]
    assert loaded_job.customer is not None
    # We expect availability to be loaded
    # print(f"Availability: {loaded_job.customer.availability}")

    # 2. Run Tool with apply=True
    with patch("src.tools.routing_tools.messaging_service") as mock_msg_service:
        mock_msg_service.enqueue_message = AsyncMock()
        mock_ts = MagicMock()
        mock_ts.render.return_value = "Successfully applied schedule"

        # Ensure we are using MockRoutingService (default if no API key)
        # We can enforce it by patching settings if needed, but default env likely doesn't have ORS key
        with patch("src.tools.routing_tools.settings") as mock_settings:
            mock_settings.openrouteservice_api_key = None

            executor = AutorouteToolExecutor(async_session, business_id, mock_ts)
            tool_input = AutorouteTool(
                date=today.isoformat(), apply=True, notify=False
            )

            report = await executor.run(tool_input)

    # 3. Verify Scheduled Time
    await async_session.refresh(j1)

    assert j1.status == JobStatus.SCHEDULED
    assert j1.scheduled_at is not None

    print(f"Scheduled at: {j1.scheduled_at}")

    # Check if scheduled time is within availability window
    # MockRoutingService defaults to 9:00 AM start, so it will likely schedule around 9:30 AM
    # We expect it to be >= 14:00

    assert j1.scheduled_at >= start_time, f"Scheduled time {j1.scheduled_at} is before availability start {start_time}"
    assert j1.scheduled_at + timedelta(minutes=j1.estimated_duration) <= end_time, f"Scheduled end time is after availability end {end_time}"
