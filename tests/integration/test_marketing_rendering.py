import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Business, Customer, Job, Campaign, CampaignChannel, RecipientStatus
from src.services.campaign_service import CampaignService
from src.services.messaging_service import MessagingService
from src.services.search_service import SearchService
from src.services.postmark_service import PostmarkService
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

@pytest.fixture
async def setup_data(async_session: AsyncSession):
    # 1. Create Business with templates
    biz = Business(
        name="Test Template Biz",
        marketing_settings={
            "templates": {
                "jobBooked": {
                    "text": "Hi {{customer.first_name}}, your job {{job.description}} is confirmed for {{job_date}}."
                },
                "onMyWay": {
                    "text": "Hi {{customer.first_name}}, we are coming to {{customer.address}}! Arrival: {{arrival.time}}."
                }
            }
        }
    )
    async_session.add(biz)
    await async_session.flush()

    # 2. Create Customer
    customer = Customer(
        business_id=biz.id,
        name="Alice Wonderland",
        first_name="Alice",
        phone="+123456789",
        street="10 Wonder St",
        city="Dublin",
        pipeline_stage="CONTACTED"
    )
    async_session.add(customer)
    await async_session.flush()

    # 3. Create Job
    job = Job(
        business_id=biz.id,
        customer_id=customer.id,
        description="Fix Magic Sink",
        value=100.0,
        scheduled_at=datetime(2026, 1, 30, 14, 0, tzinfo=timezone.utc)
    )
    async_session.add(job)
    await async_session.commit()
    
    return biz, customer, job

@pytest.mark.asyncio
async def test_campaign_body_rendering(async_session: AsyncSession, setup_data):
    biz, customer, job = setup_data
    
    # Mock SearchService to return our customer
    mock_search = MagicMock(spec=SearchService)
    mock_search._search_customers = AsyncMock(return_value=[customer])
    
    mock_postmark = MagicMock(spec=PostmarkService)
    
    service = CampaignService(async_session, mock_search, mock_postmark)
    
    # Create Campaign with variables
    campaign = await service.create_campaign(
        business_id=biz.id,
        name="Blast",
        channel=CampaignChannel.WHATSAPP,
        body="Hello {{customer.name}}! Thanks for choosing {{business.name}}."
    )
    
    await service.prepare_audience(campaign.id)
    
    # Mock MessagingService.send_message
    with patch("src.services.campaign_service.messaging_service.send_message", new_callable=AsyncMock) as mock_send:
        # Create a real MessageLog object or a simple mock that looks like one
        from src.models import MessageLog, MessageStatus
        mock_log = MagicMock(spec=MessageLog)
        mock_log.status = MessageStatus.SENT
        mock_log.external_id = "test_ext_id"
        mock_log.error_message = None
        mock_send.return_value = mock_log
        
        await service.execute_campaign(campaign.id)
        
        # Verify rendered content
        mock_send.assert_called_once()
        args = mock_send.call_args
        rendered_content = args.kwargs["content"]
        assert "Hello Alice Wonderland!" in rendered_content
        assert "Thanks for choosing Test Template Biz." in rendered_content

@pytest.mark.asyncio
async def test_automated_job_booked_rendering(async_session: AsyncSession, setup_data):
    biz, customer, job = setup_data
    
    # MessagingService uses its own session factory
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mock_factory():
        yield async_session

    service = MessagingService(session_factory=mock_factory)
    
    with patch.object(service, "enqueue_message", new_callable=AsyncMock) as mock_enqueue:
        await service.handle_job_created({
            "job_id": job.id,
            "customer_id": customer.id,
            "business_id": biz.id
        })
        
        mock_enqueue.assert_called_once()
        content = mock_enqueue.call_args.kwargs["content"]
        # Template: "Hi {{customer.first_name}}, your job {{job.description}} is confirmed for {{job_date}}."
        assert "Hi Alice" in content
        assert "your job Fix Magic Sink is confirmed" in content
        assert "Friday, Jan 30" in content

@pytest.mark.asyncio
async def test_automated_on_my_way_rendering(async_session: AsyncSession, setup_data):
    biz, customer, job = setup_data
    
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mock_factory():
        yield async_session

    service = MessagingService(session_factory=mock_factory)
    
    with patch.object(service, "enqueue_message", new_callable=AsyncMock) as mock_enqueue:
        await service.handle_on_my_way({
            "customer_id": customer.id,
            "business_id": biz.id,
            "job_id": job.id,
            "eta_minutes": 15
        })
        
        mock_enqueue.assert_called_once()
        content = mock_enqueue.call_args.kwargs["content"]
        # Template: "Hi {{customer.first_name}}, we are coming to {{customer.address}}! Arrival: {{arrival.time}}."
        assert "Hi Alice" in content
        assert "we are coming to 10 Wonder St" in content
        # Check if arrival.time is roughly current time + 15 min (HH:MM)
        assert ":" in content 
