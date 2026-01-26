from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from src.database import get_db
from src.models import User, UserRole, Business
from src.schemas.pwa import UserSchema
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

@router.get("/employees", response_model=List[UserSchema])
async def list_employees(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of all employees in the business.
    """
    stmt = select(User).where(
        User.business_id == current_user.business_id,
        User.role.in_([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])
    ).order_by(User.name.asc())
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users

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
