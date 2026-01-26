from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.expenses import ExpenseService
from src.schemas.pwa import ExpenseSchema, ExpenseCreate
from src.models import User
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

async def get_expense_service(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ExpenseService:
    return ExpenseService(session, business_id=current_user.business_id)

@router.get("/", response_model=List[ExpenseSchema])
async def list_expenses(
    search: Optional[str] = None,
    service: ExpenseService = Depends(get_expense_service)
):
    """
    List expenses for the current business.
    """
    expenses = await service.get_expenses(
        business_id=service.business_id,
        query=search
    )
    return expenses

@router.post("/", response_model=ExpenseSchema)
async def create_expense(
    expense_data: ExpenseCreate,
    service: ExpenseService = Depends(get_expense_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new expense.
    """
    description = expense_data.description
    if expense_data.vendor:
        if description:
            description = f"{expense_data.vendor}: {description}"
        else:
            description = expense_data.vendor

    expense = await service.create_expense(
        business_id=service.business_id,
        employee_id=current_user.id,
        amount=expense_data.amount,
        category=expense_data.category,
        description=description,
        job_id=expense_data.job_id,
        created_at=expense_data.date
    )
    await service.session.commit()
    return expense
