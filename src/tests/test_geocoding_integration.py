import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Business, Customer, Job, User, UserRole, JobStatus
from src.services.crm_service import CRMService
from src.tools.routing_tools import AutorouteToolExecutor
from src.services.template_service import TemplateService


@pytest.fixture
def mock_geocoder():
    with (
        patch("src.services.crm_service.GeocodingService") as mock_crm_geocoder,
        patch("src.tools.routing_tools.GeocodingService") as mock_tool_geocoder,
    ):
        instance = AsyncMock()
        instance.geocode.return_value = (
            53.3498,
            -6.2603,
            "123 Main St",
            "Dublin",
            "Ireland",
            "D1",
            "123 Main St, Dublin, Ireland, D1",
        )

        mock_crm_geocoder.return_value = instance
        mock_tool_geocoder.return_value = instance
        yield instance


@pytest.mark.asyncio
async def test_crm_service_create_job_geocoding(session: AsyncSession, mock_geocoder):
    # Setup
    biz = Business(name="Test Biz", default_city="Dublin", default_country="Ireland")
    session.add(biz)
    await session.commit()
    await session.refresh(biz)

    cust = Customer(name="Test Customer", business_id=biz.id)
    session.add(cust)
    await session.commit()
    await session.refresh(cust)

    service = CRMService(session, biz.id)

    # Act
    job = await service.create_job(
        customer_id=cust.id, description="Test Geocoding", location="Dublin, Ireland"
    )

    # Assert
    assert job.latitude == 53.3498
    assert job.longitude == -6.2603
    assert job.postal_code == "D1"
    mock_geocoder.geocode.assert_called_once()


@pytest.mark.asyncio
async def test_crm_service_update_job_geocoding(session: AsyncSession, mock_geocoder):
    # Setup
    biz = Business(name="Test Biz")
    session.add(biz)
    await session.commit()
    await session.refresh(biz)

    cust = Customer(name="Test Customer", business_id=biz.id)
    session.add(cust)

    job = Job(
        business_id=biz.id,
        customer_id=1,
        description="Initial Job",
        location="Old Location",
        latitude=1.0,
        longitude=1.0,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    service = CRMService(session, biz.id)

    # Mock different coordinates for update
    mock_geocoder.geocode.return_value = (
        51.8985,
        -8.4726,
        "Cork St",
        "Cork",
        "Ireland",
        "T12",
        "Cork St, Cork, Ireland, T12",
    )

    # Act
    updated_job = await service.update_job(job_id=job.id, location="Cork, Ireland")

    # Assert
    assert updated_job.latitude == 51.8985
    assert updated_job.longitude == -8.4726
    assert updated_job.postal_code == "T12"
    mock_geocoder.geocode.assert_called_once()


@pytest.mark.asyncio
async def test_autoroute_executor_on_the_fly_geocoding(
    session: AsyncSession, mock_geocoder
):
    # Setup
    biz = Business(name="Test Biz")
    session.add(biz)
    await session.commit()
    await session.refresh(biz)

    emp = User(email="tech@example.com", business_id=biz.id, role=UserRole.EMPLOYEE)
    session.add(emp)

    cust = Customer(name="Test Customer", business_id=biz.id)
    session.add(cust)
    await session.flush()

    # Job without coordinates but with location
    job = Job(
        business_id=biz.id,
        customer_id=cust.id,
        description="Ungeocoded Job",
        location="Dublin, Ireland",
        status=JobStatus.PENDING,
        latitude=None,
        longitude=None,
    )
    session.add(job)
    await session.commit()

    template_service = MagicMock(spec=TemplateService)
    executor = AutorouteToolExecutor(session, biz.id, template_service)

    # Configure routing service mock - use MagicMock because it's called via run_in_executor
    mock_routing = MagicMock()
    mock_routing.calculate_routes.return_value = (
        MagicMock()
    )  # Return some solution mock
    executor.routing_service = mock_routing

    # Act
    await executor._calculate(date.today())

    # Assert
    # We check the object directly as it has been updated in memory for the optimization
    assert job.latitude == 53.3498
    assert job.longitude == -6.2603
    mock_geocoder.geocode.assert_called()
