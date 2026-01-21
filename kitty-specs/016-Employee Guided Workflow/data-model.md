# Data Model Support: Employee Guided Workflow

## 1. Schema Changes

### `Service` (Extended)

We need to store the custom reminder text for each service type.

```python
class Service(Base):
    # ... existing fields ...
    
    # New Field
    reminder_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ...
```

### `User` (Verified)

No changes needed, but `timezone` field is critical.

```python
class User(Base):
    # ...
    timezone: Mapped[str] = mapped_column(String, default="UTC") # Already exists
    # ...
```

## 2. New Tool Models (Pydantic)

These will be added to `src/uimodels.py`.

### `CompleteJobTool`

Used when employee says "done #123".

```python
class CompleteJobTool(BaseModel):
    """
    Mark a job as completed. Triggered by phrases like "done #123", "finished job 123", "completed #123".
    """
    job_id: int = Field(..., description="The ID of the completed job.")
    notes: Optional[str] = Field(None, description="Optional completion notes provided by the employee.")
```

### `EditServiceTool` (Update)

Update existing tool to include `reminder_text`.

```python
class EditServiceTool(BaseModel):
    original_name: str = Field(..., description="The current name of the service to edit.")
    new_name: Optional[str] = Field(None, description="The new name for the service.")
    new_price: Optional[float] = Field(None, description="The new default price.")
    # New Field
    reminder_text: Optional[str] = Field(None, description="Auto-reminder text to send to employees for this service type.")
```

## 3. Data Flow

### Morning Shift Flow

1. **Scheduler** (06:30 local): Query `User`s with `shift_start` at this time.
2. **Query**: Fetch `jobs` for today where `employee_id` = User.id, status != 'completed', sorted by time.
3. **Generate Message**: "Good morning! You have X jobs..." + Route summary.
4. **Send**: Via `MessagingService`.

### Completion Flow

1. **Input**: "Done #123"
2. **Tool**: `CompleteJobTool(job_id=123)`
3. **Action**:
    - Update Job status -> "completed".
    - Find NEXT job for Employee for Today (status='pending'/'scheduled').
4. **Response**:
    - "Job #123 marked done."
    - IF next_job: "Next up: [Customer] at [Address]. [Map Link]. REMINDER: [Service.reminder_text]"
