import pytest
from unittest.mock import MagicMock, AsyncMock
from src.api.v1.pwa.dashboard import get_dashboard_stats
from src.models import PipelineStage, User, UserRole

@pytest.mark.asyncio
async def test_get_dashboard_stats_logic():
    # Mock user
    user = User(business_id=1, role=UserRole.OWNER)

    # Mock DB
    db = AsyncMock()

    # Mock result for revenue query
    # It returns a scalar result (sum)
    mock_revenue_result = MagicMock()
    mock_revenue_result.scalar.return_value = 5000.0

    # Mock result for pipeline query
    # It returns list of (stage, count)
    mock_pipeline_result = MagicMock()
    mock_pipeline_result.all.return_value = [
        (PipelineStage.NEW_LEAD, 10),
        (PipelineStage.CONTACTED, 5),
        (PipelineStage.LOST, 2)
    ]

    # Configure side_effect to return different mocks for different calls
    # The function calls db.execute twice.
    # 1. Revenue
    # 2. Pipeline
    db.execute.side_effect = [mock_revenue_result, mock_pipeline_result]

    stats = await get_dashboard_stats(user=user, db=db)

    assert stats["revenue_monthly"] == 5000.0

    # Check pipeline breakdown
    assert stats["pipeline_breakdown"][PipelineStage.NEW_LEAD.name] == 10
    assert stats["pipeline_breakdown"][PipelineStage.CONTACTED.name] == 5
    assert stats["pipeline_breakdown"][PipelineStage.LOST.name] == 2
    assert stats["pipeline_breakdown"][PipelineStage.QUOTED.name] == 0 # Defaulted to 0

    # Check active leads count
    # Active = NEW_LEAD (10) + NOT_CONTACTED (0) + CONTACTED (5) + QUOTED (0) = 15
    assert stats["active_leads_count"] == 15
