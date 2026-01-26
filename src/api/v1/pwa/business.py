from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List

from src.database import get_db
from src.models import User, UserRole, Business, WageConfiguration, WageModelType
from src.schemas.pwa import UserSchema, WageConfigurationUpdate
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

@router.get("/employees", response_model=List[UserSchema])
async def list_employees(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of all employees in the business, including their wage configurations.
    """
    stmt = select(User).where(
        User.business_id == current_user.business_id,
        User.role.in_([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])
    ).options(selectinload(User.wage_config)).order_by(User.name.asc())
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users

@router.patch("/employees/{employee_id}/wage-config")
async def update_wage_config(
    employee_id: int,
    update_data: WageConfigurationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates or creates the wage configuration for a specific employee.
    Only owners and managers can update other employees' configs.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only owners and managers can update wage configurations")
    
    # Ensure employee is in the same business
    employee = await db.get(User, employee_id)
    if not employee or employee.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Get or create wage config
    stmt = select(WageConfiguration).where(WageConfiguration.user_id == employee_id)
    result = await db.execute(stmt)
    wage_config = result.scalar_one_or_none()

    if not wage_config:
        wage_config = WageConfiguration(user_id=employee_id)
        db.add(wage_config)

    # Update fields
    if update_data.model_type is not None:
        wage_config.model_type = WageModelType(update_data.model_type)
    if update_data.rate_value is not None:
        wage_config.rate_value = update_data.rate_value
    if update_data.tax_withholding_rate is not None:
        wage_config.tax_withholding_rate = update_data.tax_withholding_rate
    if update_data.allow_expense_claims is not None:
        wage_config.allow_expense_claims = update_data.allow_expense_claims

    await db.commit()
    return {"status": "success", "wage_config": {
        "model_type": wage_config.model_type,
        "rate_value": wage_config.rate_value,
        "tax_withholding_rate": wage_config.tax_withholding_rate,
        "allow_expense_claims": wage_config.allow_expense_claims
    }}

@router.get("/info")
async def get_business_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns general business information including seat counts.
    """
    business = await db.get(Business, current_user.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    # Count actual employees
    employee_count_stmt = select(func.count(User.id)).where(User.business_id == business.id)
    employee_count_result = await db.execute(employee_count_stmt)
    employee_count = employee_count_result.scalar() or 0

    return {
        "seat_count": business.seat_limit,
        "employee_count": employee_count,
        "business_name": business.name
    }
