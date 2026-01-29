import pytest
from datetime import datetime, timezone
from src.models import Business, User, Job, UserRole, JobStatus
from src.services.assignment_service import AssignmentService

# Mark all tests as async
pytestmark = pytest.mark.asyncio


async def setup_data(session):
    # Create business
    biz = Business(name="Test Biz")
    session.add(biz)
    await session.flush()

    # Create employees
    user1 = User(
        business_id=biz.id,
        name="John Doe",
        email="john@example.com",
        phone_number="1234567890",
        role=UserRole.EMPLOYEE,
    )
    user2 = User(
        business_id=biz.id,
        name="Bob Builder",
        email="bob@example.com",
        phone_number="0987654321",
        role=UserRole.EMPLOYEE,
    )
    user3 = User(
        business_id=biz.id,
        name="Johnny Bravo",
        email="johnny@cartoon.com",
        phone_number="1122334455",
        role=UserRole.EMPLOYEE,
    )

    session.add_all([user1, user2, user3])
    await session.commit()
    return biz, user1, user2, user3


async def test_find_employee_by_name(async_session):
    biz, user1, user2, user3 = await setup_data(async_session)
    service = AssignmentService(async_session, biz.id)

    # Search "John" -> should find John Doe and Johnny Bravo
    results = await service.find_employee_by_name("John")
    assert len(results) == 2
    names = sorted([u.name for u in results])
    assert names == ["John Doe", "Johnny Bravo"]

    # Search "Bob"
    results = await service.find_employee_by_name("Bob")
    assert len(results) == 1
    assert results[0].name == "Bob Builder"

    # Search by email fragment
    results = await service.find_employee_by_name("cartoon")
    assert len(results) == 1
    assert results[0].name == "Johnny Bravo"


async def test_assign_job_success(async_session):
    biz, user1, _, _ = await setup_data(async_session)
    service = AssignmentService(async_session, biz.id)

    # Create customer (implicitly required by User FK check? No, Job needs Customer)
    # Wait, simple Job test might fail if Customer FK fails.
    # Let's create a minimal customer if Job needs it.
    # Job model: customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    from src.models import Customer

    cust = Customer(name="Cust", business_id=biz.id)
    async_session.add(cust)
    await async_session.flush()

    job = Job(
        business_id=biz.id,
        customer_id=cust.id,
        description="Fix sink",
        status=JobStatus.PENDING,
    )
    async_session.add(job)
    await async_session.commit()

    res = await service.assign_job(job.id, user1.id)
    assert res.success
    assert res.job.employee_id == user1.id
    assert res.warning is None


async def test_assign_job_validation(async_session):
    biz, user1, _, _ = await setup_data(async_session)

    # Another business
    biz2 = Business(name="Other Biz")
    async_session.add(biz2)
    await async_session.flush()
    user_other = User(business_id=biz2.id, name="Other Guy", email="other@guy.com")
    async_session.add(user_other)
    await async_session.commit()

    service = AssignmentService(async_session, biz.id)

    from src.models import Customer

    cust = Customer(name="Cust", business_id=biz.id)
    async_session.add(cust)
    await async_session.flush()

    job = Job(business_id=biz.id, customer_id=cust.id, description="Fix sink")
    async_session.add(job)
    await async_session.commit()

    # Attempt assigning user from other business
    res = await service.assign_job(job.id, user_other.id)
    assert not res.success
    assert "not in business" in res.error


async def test_assign_job_conflict(async_session):
    biz, user1, _, _ = await setup_data(async_session)
    service = AssignmentService(async_session, biz.id)

    from src.models import Customer

    cust = Customer(name="Cust", business_id=biz.id)
    async_session.add(cust)
    await async_session.flush()

    ts = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)

    # Job 1 assigned to User 1
    job1 = Job(
        business_id=biz.id,
        customer_id=cust.id,
        description="Job 1",
        scheduled_at=ts,
        employee_id=user1.id,
    )
    async_session.add(job1)
    await async_session.commit()

    # Job 2 unassigned, same time
    job2 = Job(
        business_id=biz.id, customer_id=cust.id, description="Job 2", scheduled_at=ts
    )
    async_session.add(job2)
    await async_session.commit()

    # Assign Job 2 to User 1
    res = await service.assign_job(job2.id, user1.id)

    # Should succeed but warn
    assert res.success
    assert res.warning == "Double booked"
    assert res.job.employee_id == user1.id


async def test_assign_job_no_conflict_different_time(async_session):
    biz, user1, _, _ = await setup_data(async_session)
    service = AssignmentService(async_session, biz.id)

    from src.models import Customer

    cust = Customer(name="Cust", business_id=biz.id)
    async_session.add(cust)
    await async_session.flush()

    ts1 = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2023, 10, 10, 12, 0, 0, tzinfo=timezone.utc)

    job1 = Job(
        business_id=biz.id,
        customer_id=cust.id,
        description="Job 1",
        scheduled_at=ts1,
        employee_id=user1.id,
    )
    async_session.add(job1)
    await async_session.commit()

    job2 = Job(
        business_id=biz.id, customer_id=cust.id, description="Job 2", scheduled_at=ts2
    )
    async_session.add(job2)
    await async_session.commit()

    res = await service.assign_job(job2.id, user1.id)
    assert res.success
    assert res.warning is None
