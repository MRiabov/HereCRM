import pytest
from unittest.mock import AsyncMock, patch
from src.tools.quote_tools import CreateQuoteTool
from src.uimodels import CreateQuoteTool, QuoteLineItemInput
from src.services.quote_service import QuoteService
from src.models import Business, Customer, QuoteStatus, User
from src.tool_executor import ToolExecutor
from src.services.template_service import TemplateService

@pytest.mark.asyncio
async def test_quote_full_conversational_flow(async_session):
    """
    Verifies the end-to-end flow of the Conversational Quotations feature (Spec 012).
    Flow:
    1. User (Agent) triggers CreateQuoteTool -> Quote created (Draft/Sent).
    2. User (Simulated) triggers Confirm Quote -> Job created.
    """
    
    # 1. Setup Data
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(
        name="John Doe", 
        phone="+1234567890", 
        business_id=business.id,
        street="123 Main St"
    )
    async_session.add(customer)
    
    user = User(
        email="test@example.com", 
        business_id=business.id, 
        role="owner",
        preferences={"default_city": "Dublin", "default_country": "Ireland"}
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(customer)
    await async_session.refresh(user)

    # 2. Setup Tool Executor
    template_service = TemplateService()
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=user.id,
        user_phone=user.phone_number or "",
        template_service=template_service
    )

    # 3. Step 1: LLM triggers Create Quote
    #   "Send a quote to John Doe for 2 hours of Cleaning at 50/hr"
    input_data = CreateQuoteTool(
        customer_identifier="John Doe",
        items=[
            QuoteLineItemInput(description="Cleaning", quantity=2, price=50.0)
        ]
    )

    # Mocking external notifications (WhatsApp/PDF) to avoid actual API calls/failures
    with patch("src.services.quote_service.QuoteService.send_quote", new_callable=AsyncMock) as mock_send:
        msg, data = await executor.execute(input_data)
        
        # Verify Tool Output
        assert "Quote #" in msg
        assert "John Doe" in msg
        assert data["action"] == "create_quote"
        quote_id = data["id"]
        assert quote_id is not None
        
        # Verify Quote in DB
        quote_service = QuoteService(async_session)
        quote = await quote_service.get_quote(quote_id)
        assert quote is not None
        assert quote.customer_id == customer.id
        assert quote.total_amount == 100.0 # 2 * 50
        assert quote.status == QuoteStatus.DRAFT # Or SENT depending on flow, usually Draft then sent
        
        # Note: In real flow, create_quote might enable sending immediately or separate.
        # The tool implementation calls send_quote if available.
        mock_send.assert_awaited()

    # 4. Step 2: Customer confirms quote
    #   (Simulating the Confirm Action, usually via Webhook or Link click)
    confirm_result = await quote_service.confirm_quote(quote.external_token)
    
    assert confirm_result is not None
    assert confirm_result.status == QuoteStatus.ACCEPTED
    assert confirm_result.job_id is not None
    
    # 5. Verify Job Creation
    from src.repositories import JobRepository
    job_repo = JobRepository(async_session)
    job = await job_repo.get_by_id(confirm_result.job_id, business.id)
    
    assert job is not None
    assert job.customer_id == customer.id
    assert job.value == 100.0
    assert "Job from Quote" in job.description
    # Check line items on job
    # Depending on how logic copies them.
    # We need to refresh/load relations if lazy
    await async_session.refresh(job, ["line_items"])
    assert len(job.line_items) == 1
    assert job.line_items[0].description == "Cleaning"

    print("\n✅ Full Conversational Quote Flow Verified Successfully!")
