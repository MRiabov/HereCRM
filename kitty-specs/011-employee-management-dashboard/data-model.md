# Data Model: Employee Management Dashboard

**Feature Branch**: `011-employee-management-dashboard`
**Date**: 2026-01-20

## Schema Changes

### 1. ConversationStatus Enum (Update)

Add a new status to manage the "Dashboard Screen" state.

```python
class ConversationStatus(str, enum.Enum):
    # ... existing ...
    EMPLOYEE_MANAGEMENT = "employee_management"  # NEW
```

### 2. Job Entity (Update)

Link jobs to specific employees (app users) and ensure scheduling time is trackable.

```python
class Job(Base):
    __tablename__ = "jobs"
    
    # ... existing ...
    
    # NEW: Link to the employee performing the job
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    # EXISTING (Verify usage):
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime) 
    
    # Relationships
    employee: Mapped[Optional["User"]] = relationship(foreign_keys=[employee_id])
```

### 3. User Entity (Usage Only)

No schema changes, but logic relies on `UserRole`:

```python
class UserRole(str, enum.Enum):
    OWNER = "owner"     # Can Assign
    MEMBER = "member"   # Can Be Assigned To
```

## Validation Rules

1. **Role Check**: `job.employee_id` MUST be a User with `role='member'` (or possibly `owner` if they do field work). Application logic should validate candidates are "assignable".
2. **Conflict Warning**: Assigning a job to a time slot that overlaps with another job for the same employee should trigger a warning (soft validation), not a hard DB error.
3. **Availability**: Jobs can only be assigned to valid, active users of the same `business_id`.

## State Transitions

- **Enter Dashboard**: `IDLE` -> `EMPLOYEE_MANAGEMENT`
  - Trigger: "Manage employees", "Show schedule"
- **Exit Dashboard**: `EMPLOYEE_MANAGEMENT` -> `IDLE`
  - Trigger: "Back", "Exit", "Done"
