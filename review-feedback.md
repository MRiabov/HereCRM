**Issue 1: Async Safety and Blocking Calls**
The `GoogleCalendarService` methods `create_event`, `update_event`, and `delete_event` use blocking calls from the Google API client (`build().execute()`). Since HereCRM is an async FastAPI application, these calls will block the event loop.
*Fix*: Make these methods `async def` and use `asyncio.to_thread` for the blocking bits, or wrap the service calls in `asyncio.to_thread` in the caller.

**Issue 2: Synchronous Lazy Loading Pitfall**
In `_build_event_body`, the code accesses `job.customer.name`. In an async SQLAlchemy environment, accessing a relationship like `job.customer` synchronously will raise a `MissingGreenlet` error if it wasn't pre-loaded (e.g., via `selectinload`).
*Fix*: Make `_build_event_body` (and its callers) async so you can load the customer if missing, or ensure the Job is always passed with a loaded customer.

**Issue 3: Broken/Redundant Migrations**
The migration `fde7d267dc45` attempts to add the `message_credits` column to `businesses`, which is already added by its parent migration `6675461aad32`. This will cause deployment failures. Additionally, there is an empty migration `b95d17b4d850` on top.
*Fix*: Clean up the migrations to only add the fields required for this feature (`google_calendar_credentials`, `google_calendar_sync_enabled`, `gcal_event_id`) and avoid re-adding existing columns.

**Issue 4: Duplicate Model Definition**
In `src/models/__init__.py`, the `gcal_event_id` field is defined twice in the `Job` class (lines 282 and 288).
*Fix*: Remove the duplicate definition.

**Issue 5: Token Refresh Persistence**
The `_get_credentials` method refreshes expired tokens using `creds.refresh(Request())`, but it doesn't save the new credentials back to the database. This means every subsequent call will re-trigger a refresh.
*Fix*: Implement a mechanism to persist the updated credentials when a refresh occurs (this likely requires passing an `AsyncSession` or using a repository).
