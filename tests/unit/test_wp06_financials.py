import pytest
from unittest.mock import MagicMock, AsyncMock
from src.services.crm_service import CRMService
from src.models import Job, Expense, LedgerEntry, LedgerEntryType

@pytest.mark.asyncio
async def test_get_job_profitability():
    # Mock Session
    mock_session = AsyncMock()
    
    # Mock Data
    job = Job(id=1, value=1000.0, business_id=1)
    # Mock line items? simplistic test assumes job.value is total revenue for now based on service implementation
    
    # Mock Repo
    with pytest.MonkeyPatch.context() as m:
        # Mock JobRepository get_by_id
        mock_job_repo_cls = MagicMock()
        mock_job_repo = MagicMock()
        mock_job_repo.get_by_id = AsyncMock(return_value=job)
        mock_job_repo_cls.return_value = mock_job_repo
        
        m.setattr("src.services.crm_service.JobRepository", mock_job_repo_cls)
        
        service = CRMService(mock_session, business_id=1)
        # Verify repo was assigned
        service.job_repo = mock_job_repo 
        
        # Mock Session execute used for expenses and ledger
        # We need to mock the returns order: first expenses, then labor
        
        mock_expense_result = MagicMock()
        mock_expense_result.scalars.return_value.all.return_value = [
            Expense(amount=100.0, job_id=1),
            Expense(amount=50.0, job_id=1)
        ]
        
        mock_labor_result = MagicMock()
        mock_labor_result.scalars.return_value.all.return_value = [
            LedgerEntry(amount=200.0, job_id=1, entry_type=LedgerEntryType.WAGE)
        ]
        
        mock_session.execute.side_effect = [mock_expense_result, mock_labor_result]

        # ACT
        result = await service.get_job_profitability(1)
        
        # ASSERT
        assert result["revenue"] == 1000.0
        assert result["cost_expenses"] == 150.0
        assert result["cost_labor"] == 200.0
        assert result["net_profit"] == 1000.0 - 150.0 - 200.0 # 650.0
