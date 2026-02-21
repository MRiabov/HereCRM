import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import PipelineStage, Customer, Business
from src.services.pipeline_handlers import handle_job_created, handle_contact_event, handle_quote_sent


@pytest.mark.asyncio
async def test_handle_job_created_first_job():
    """Test that customer moves to CONVERTED_ONCE when they have 1 job."""
    # Mock session
    mock_session = AsyncMock()
    # Ensure __aenter__ returns the session itself
    mock_session.__aenter__.return_value = mock_session

    # Mock repositories
    mock_job_repo_cls = MagicMock()
    mock_customer_repo_cls = MagicMock()

    mock_job_repo = AsyncMock()
    mock_customer_repo = AsyncMock()

    mock_job_repo_cls.return_value = mock_job_repo
    mock_customer_repo_cls.return_value = mock_customer_repo

    # Setup data
    customer = Customer(id=1, business_id=1, pipeline_stage=PipelineStage.NOT_CONTACTED)
    mock_job_repo.get_count_by_customer.return_value = 1
    mock_customer_repo.get_by_id.return_value = customer

    # Patch
    # AsyncSessionLocal is called to get a context manager.
    # The context manager's __aenter__ yields the session.
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    with (
        patch(
            "src.services.pipeline_handlers.src.database.AsyncSessionLocal",
            mock_session_factory,
        ),
        patch("src.services.pipeline_handlers.JobRepository", mock_job_repo_cls),
        patch(
            "src.services.pipeline_handlers.CustomerRepository", mock_customer_repo_cls
        ),
    ):
        event_data = {"customer_id": 1, "business_id": 1}
        await handle_job_created(event_data)

        # Verify
        assert customer.pipeline_stage == PipelineStage.CONVERTED_ONCE
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_job_created_multiple_jobs():
    """Test that customer moves to CONVERTED_RECURRENT when they have >1 jobs."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session

    mock_job_repo_cls = MagicMock()
    mock_customer_repo_cls = MagicMock()

    mock_job_repo = AsyncMock()
    mock_customer_repo = AsyncMock()

    mock_job_repo_cls.return_value = mock_job_repo
    mock_customer_repo_cls.return_value = mock_customer_repo

    customer = Customer(
        id=1, business_id=1, pipeline_stage=PipelineStage.CONVERTED_ONCE
    )
    mock_job_repo.get_count_by_customer.return_value = 2
    mock_customer_repo.get_by_id.return_value = customer

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    with (
        patch(
            "src.services.pipeline_handlers.src.database.AsyncSessionLocal",
            mock_session_factory,
        ),
        patch("src.services.pipeline_handlers.JobRepository", mock_job_repo_cls),
        patch(
            "src.services.pipeline_handlers.CustomerRepository", mock_customer_repo_cls
        ),
    ):
        event_data = {"customer_id": 1, "business_id": 1}
        await handle_job_created(event_data)

        assert customer.pipeline_stage == PipelineStage.CONVERTED_RECURRENT
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_contact_event():
    """Test that customer moves to CONTACTED if currently NOT_CONTACTED."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session

    mock_customer_repo_cls = MagicMock()
    mock_customer_repo = AsyncMock()
    mock_customer_repo_cls.return_value = mock_customer_repo

    customer = Customer(id=1, business_id=1, pipeline_stage=PipelineStage.NOT_CONTACTED)
    mock_customer_repo.get_by_id.return_value = customer

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    with (
        patch(
            "src.services.pipeline_handlers.src.database.AsyncSessionLocal",
            mock_session_factory,
        ),
        patch(
            "src.services.pipeline_handlers.CustomerRepository", mock_customer_repo_cls
        ),
    ):
        event_data = {"customer_id": 1, "business_id": 1}
        await handle_contact_event(event_data)

        assert customer.pipeline_stage == PipelineStage.CONTACTED
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_contact_event_no_op():
    """Test that contact event does NOTHING if customer is already beyond NOT_CONTACTED."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session

    mock_customer_repo_cls = MagicMock()
    mock_customer_repo = AsyncMock()
    mock_customer_repo_cls.return_value = mock_customer_repo

    customer = Customer(id=1, business_id=1, pipeline_stage=PipelineStage.CONTACTED)
    mock_customer_repo.get_by_id.return_value = customer

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    with (
        patch(
            "src.services.pipeline_handlers.src.database.AsyncSessionLocal",
            mock_session_factory,
        ),
        patch(
            "src.services.pipeline_handlers.CustomerRepository", mock_customer_repo_cls
        ),
    ):
        event_data = {"customer_id": 1, "business_id": 1}
        await handle_contact_event(event_data)

        mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_contact_event_from_new_lead():
    """
    Test that a customer in NEW_LEAD stage moves to CONTACTED when a contact event occurs.
    """
    # Mock session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.commit = AsyncMock()

    # Mock Repositories
    mock_customer_repo = AsyncMock()

    # Setup Customer in NEW_LEAD stage
    customer = Customer(id=1, business_id=1, pipeline_stage=PipelineStage.NEW_LEAD)
    mock_customer_repo.get_by_id.return_value = customer

    # Mock session maker
    # session_maker() returns mock_session (which is an async context manager)
    mock_session_maker = MagicMock(return_value=mock_session)

    # Mock get_session_maker function
    # It is async, so it returns a coroutine that resolves to mock_session_maker
    mock_get_session_maker_func = AsyncMock(return_value=mock_session_maker)

    with patch("src.services.pipeline_handlers.src.database.get_session_maker", side_effect=mock_get_session_maker_func), \
         patch("src.services.pipeline_handlers.CustomerRepository", return_value=mock_customer_repo):

        event_data = {"customer_id": 1, "business_id": 1}
        await handle_contact_event(event_data)

        # Assertion: Should be CONTACTED
        assert customer.pipeline_stage == PipelineStage.CONTACTED
        mock_session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_quote_sent_uses_correct_session_maker():
    """
    Test that handle_quote_sent uses get_session_maker.
    """
    # Mock session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.commit = AsyncMock()

    mock_customer_repo = AsyncMock()
    mock_business_repo = AsyncMock()

    customer = Customer(id=1, business_id=1, pipeline_stage=PipelineStage.CONTACTED)
    business = Business(id=1, workflow_pipeline_quoted_stage=True)

    mock_customer_repo.get_by_id.return_value = customer
    mock_business_repo.get_by_id.return_value = business

    mock_session_maker = MagicMock(return_value=mock_session)
    mock_get_session_maker_func = AsyncMock(return_value=mock_session_maker)

    with patch("src.services.pipeline_handlers.src.database.get_session_maker", side_effect=mock_get_session_maker_func) as mock_get_session_maker, \
         patch("src.services.pipeline_handlers.CustomerRepository", return_value=mock_customer_repo), \
         patch("src.services.pipeline_handlers.BusinessRepository", return_value=mock_business_repo):

        event_data = {"customer_id": 1, "business_id": 1}
        await handle_quote_sent(event_data)

        # Verify get_session_maker was called and awaited
        mock_get_session_maker.assert_awaited_once()
