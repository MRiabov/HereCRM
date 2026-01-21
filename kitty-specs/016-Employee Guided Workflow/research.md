# Research Phase: Employee Guided Workflow

## 1. Triggering Shift Starts (APScheduler)

**Context**: We need a reliable way to trigger an event at 6:30 AM local time for every employee.
**Finding**:

- `APScheduler` is NOT currently installed in the environment (checked via `pip show`).
- The project uses `FastAPI` and `asyncio`.
- **Decision**: We will add `APScheduler` (AsyncIOScheduler) to valid dependencies. It will run in the main utility loop.
- **Implementation Pattern**:

    ```python
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_shifts, 'cron', minute='*/15') # Check periodically or schedule exact times dynamically
    scheduler.start()
    ```

- **Alternative**: We could schedule exact jobs for each employee, but a polling job every 15-30 mins that checks "Is it 06:30 for any user now?" might be simpler and more robust to restarts, provided we store "last_shift_notification" date to avoid duplicates.

## 2. Timezone Handling

**Context**: Employees may be in different timezones.
**Finding**:

- The `User` model in `src/models.py` already possesses a `timezone` field:

    ```python
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    ```

- **Decision**: We will use this existing field. The "Shift Starter" logic must convert 06:30 AM target time to UTC for the scheduler, or use the scheduler's timezone support.

## 3. Proactive Messaging

**Context**: System must send messages without a preceding user message.
**Finding**:

- `MessagingService` class exists in `src/services/messaging_service.py`.
- It has `send_message` and `enqueue_message` methods.
- It is already registered in `lifespan` and runs a background queue worker.
- **Decision**: We can simply inject `MessagingService` into our `ShiftService` (or `SchedulerService`) and call `enqueue_message(phone, content, trigger_source="scheduled_shift")`.

## 4. Job Completion Tool

**Context**: Parsing "done #123".
**Finding**:

- `tool_executor.py` processes tool calls.
- There is no specific `CompleteJobTool`.
- `AddJobTool` and `ScheduleJobTool` exist.
- **Decision**: Create a new `CompleteJobTool` taking `job_id`. The LLM should be prompt-engineered (in system prompt) to map "done #123" -> `CompleteJobTool(job_id=123)`.

## 5. Service Reminders

**Context**: Configurable reminders per service type.
**Finding**:

- `Service` model in `src/models.py` has `name`, `default_price`, `estimated_duration`.
- **Decision**: Add `reminder_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to `Service` model.
- **Tooling**: Update `EditServiceTool` in `src/uimodels.py` to accept `reminder_text`.
