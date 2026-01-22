from pydantic.v1 import BaseModel, Field
from typing import Optional

class ShowScheduleTool(BaseModel):
    """Show the schedule for all employees for today.
    Use this when the user wants to see what the team is doing or check availability."""
    
    date: Optional[str] = Field(
        None, description="The date to show the schedule for in YYYY-MM-DD format. Defaults to today."
    )

class AssignJobTool(BaseModel):
    """Assign a specific job to an employee by name.
    Use this when the user says 'Assign job #123 to John' or similar."""

    job_id: int = Field(..., description="The ID of the job to assign")
    assign_to_name: str = Field(..., description="The name of the employee to assign the job to")

class InviteUserTool(BaseModel):
    """Invite a new person to join the business as an employee.
    Use this when the user says 'Invite +123456789'."""
    
    identifier: str = Field(..., description="The phone number or email of the person to invite")

class JoinBusinessTool(BaseModel):
    """Join a business from an invitation.
    Use this when the user says 'Join' or 'Accept invitation'."""
    pass

class ExitEmployeeManagementTool(BaseModel):
    """Exit the employee management mode.
    Use this when the user says 'exit', 'quit', 'back', or 'done'."""
    pass
