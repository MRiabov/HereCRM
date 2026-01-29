from pydantic.v1 import BaseModel, Field
from typing import Optional


class ShowScheduleTool(BaseModel):
    """Show the schedule for all employees for today.
    Use this when the user wants to see what the team is doing or check availability."""

    date: Optional[str] = Field(
        None,
        description="The date to show the schedule for in YYYY-MM-DD format. Defaults to today.",
    )


class AssignJobTool(BaseModel):
    """Assign a specific job to an employee by name.
    Use this when the user says 'Assign job #123 to John' or similar."""

    job_id: int = Field(..., description="The ID of the job to assign")
    assign_to_name: str = Field(
        ..., description="The name of the employee to assign the job to"
    )


class InviteUserTool(BaseModel):
    """Invite a new person to join the business as an employee.
    Use this when the user says 'Invite +123456789'."""

    identifier: str = Field(
        ..., description="The phone number or email of the person to invite"
    )


class JoinBusinessTool(BaseModel):
    """Join a business from an invitation.
    Use this when the user says 'Join' or 'Accept invitation'."""

    pass


class PromoteUserTool(BaseModel):
    """Promote an employee to a manager role.
    Use this when the owner says 'Make John a manager' or 'Promote Sarah'."""

    employee_query: str = Field(
        ..., description="The name or phone number of the employee to promote"
    )


class DismissUserTool(BaseModel):
    """Dismiss/Remove an employee from the business.
    Use this when the owner says 'Fire John', 'Remove Sarah from the team', etc.
    This revokes their access to the business."""

    employee_query: str = Field(
        ..., description="The name or phone number of the employee to dismiss"
    )


class LeaveBusinessTool(BaseModel):
    """Leave the current business.
    Use this when an employee says 'I want to quit', 'Leave business', etc.
    This removes the current user from the business."""

    pass


class ExitEmployeeManagementTool(BaseModel):
    """Exit the employee management mode.
    Use this when the user says 'exit', 'quit', 'back', or 'done'."""

    pass
