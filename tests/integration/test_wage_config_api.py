import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models import User, UserRole, WageModelType
from src.schemas.pwa import WageConfigurationUpdate


@pytest.mark.asyncio
async def test_update_wage_config():
    """
    Test updating an employee's wage configuration.
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.delete = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.business_id = 1
    mock_user.role = UserRole.OWNER

    mock_employee = MagicMock(spec=User)
    mock_employee.id = 2
    mock_employee.business_id = 1
    mock_employee.wage_config = None

    # Mock db.get for the employee
    mock_db.get.return_value = mock_employee

    # Mock db.execute for existing wage_config
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    from src.api.v1.pwa.business import update_wage_config

    update_data = WageConfigurationUpdate(
        model_type="HOURLY_PER_JOB",
        rate_value=25.0,
        tax_withholding_rate=15.0,
        allow_expense_claims=True,
    )

    response = await update_wage_config(
        employee_id=2, update_data=update_data, current_user=mock_user, db=mock_db
    )

    assert response["status"] == "SUCCESS"
    assert response["wage_config"]["rate_value"] == 25.0
    assert response["wage_config"]["model_type"] == WageModelType.HOURLY_PER_JOB

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
