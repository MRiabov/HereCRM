import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tool_executor import ToolExecutor
from src.models import Business, UserRole


@pytest.mark.asyncio
async def test_tool_executor_prioritizes_business_defaults():
    session = AsyncMock()
    template_service = MagicMock()

    # Mock user preferences
    user = MagicMock()
    user.id = 1
    user.role = UserRole.OWNER
    user.preferences = {"default_city": "User City", "default_country": "User Country"}

    # Mock business with different defaults
    business = MagicMock(spec=Business)
    business.id = 1
    business.default_city = "Business City"
    business.default_country = "Business Country"

    executor = ToolExecutor(
        session,
        business_id=1,
        user_id=1,
        user_phone="+123456789",
        template_service=template_service,
    )

    # Mock repositories
    executor.user_repo = AsyncMock()
    executor.user_repo.get_by_id.return_value = user

    # Mock business fetch
    session.get.return_value = business

    # Call internal method to get defaults
    city, country, safeguard, max_dist = await executor._get_user_defaults()

    assert city == "Business City"
    assert country == "Business Country"


@pytest.mark.asyncio
async def test_tool_executor_falls_back_to_user_defaults():
    session = AsyncMock()
    template_service = MagicMock()

    # Mock user preferences
    user = MagicMock()
    user.id = 1
    user.role = UserRole.OWNER
    user.preferences = {"default_city": "User City", "default_country": "User Country"}

    # Mock business with NO defaults
    business = MagicMock(spec=Business)
    business.id = 1
    business.default_city = None
    business.default_country = None

    executor = ToolExecutor(
        session,
        business_id=1,
        user_id=1,
        user_phone="+123456789",
        template_service=template_service,
    )

    # Mock repositories
    executor.user_repo = AsyncMock()
    executor.user_repo.get_by_id.return_value = user

    # Mock business fetch
    session.get.return_value = business

    # Call internal method to get defaults
    city, country, safeguard, max_dist = await executor._get_user_defaults()

    assert city == "User City"
    assert country == "User Country"
