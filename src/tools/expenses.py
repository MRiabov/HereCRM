from typing import Tuple, Optional, Dict, Any
from src.uimodels import AddExpenseTool
from src.services.expenses import ExpenseService

class ExpenseTools:
    def __init__(self, expense_service: ExpenseService):
        self.expense_service = expense_service

    async def add_expense(
        self,
        tool: AddExpenseTool,
        employee_id: int
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Execute the AddExpenseTool.
        """
        expense = await self.expense_service.create_expense(
            business_id=self.expense_service.business_id,
            employee_id=employee_id,
            amount=tool.amount,
            category=tool.category,
            description=tool.description,
            job_id=tool.job_id
        )

        job_info = f" (Linked to Job #{tool.job_id})" if tool.job_id else ""
        message = f"✔ Recorded expense: {tool.description} ({tool.category.value if hasattr(tool.category, 'value') else tool.category}) - €{tool.amount:.2f}{job_info}"
        
        return message, {
            "action": "create",
            "entity": "expense",
            "id": expense.id,
            "amount": expense.amount,
            "description": expense.description,
            "category": expense.category,
            "job_id": expense.job_id,
            "employee_id": expense.employee_id
        }