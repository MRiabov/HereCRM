from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Expense
from src.repositories import ExpenseRepository

class ExpenseService:
    def __init__(self, session: AsyncSession, business_id: int):
        self.session = session
        self.business_id = business_id
        self.expense_repo = ExpenseRepository(session)

    async def create_expense(
        self,
        business_id: int,
        employee_id: int,
        amount: float,
        category: str,
        description: Optional[str] = None,
        job_id: Optional[int] = None,
        receipt_url: Optional[str] = None,
    ) -> Expense:
        """
        Record a new expense.
        """
        expense = Expense(
            business_id=business_id,
            employee_id=employee_id,
            job_id=job_id,
            amount=amount,
            category=category,
            description=description,
            receipt_url=receipt_url,
            created_at=datetime.now(timezone.utc)
        )
        self.expense_repo.add(expense)
        await self.session.flush()
        return expense

    async def get_expenses(
        self,
        business_id: int,
        job_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
    ) -> List[Expense]:
        """
        Get expenses with optional filters.
        """
        return await self.expense_repo.get_expenses(
            business_id=business_id,
            job_id=job_id,
            employee_id=employee_id,
            min_date=min_date,
            max_date=max_date
        )
