# Implementation Plan - Live Location Tracking

## Technical Context

We are implementing live location tracking for employees to enable automated ETA updates for customers. This feature depends on:

1. **WhatsApp Direct API Integration**: Receiving location coordinates from user messages.
2. **OpenRouteService (ORS)**: Calculating driving times between current employee location and customer address.
3. **Spec 013 Alignment**: Spec 013 (Autoroute) introduces `OpenRouteServiceAdapter`. We MUST reuse or extend this infrastructure.

**Constraints & assumptions:**

- **Spec 013 Dependency**: Spec 013 is in progress. We assume we can pull its code (models/services) as a base. If not available, we must implement a compatible scaffolding.
- **Location Source**: We rely on WhatsApp Cloud API `location` message type.
- **Fallback**: Static Google Maps links via SMS (Twilio) must be parsed.

## Constitution Check

N/A - No constitution file present.

## Architecture

### 1. Data Model Updates (`User`)

We will add fields to the existing `User` model to store the last known location.

```python
class User(Base):
    # ... existing fields ...
    current_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

### 2. Services

- **`LocationService`**: New service.
  - `update_location(user_id, lat, lng)`: Updates DB fields.
  - `parse_location_from_text(text)`: Extracts coords from Google Maps shortlinks (for SMS fallback).
  - `get_employee_location(user_id)`: Returns current coords and freshness.

- **`RoutingService` (Shared with 013)**:
  - We will assume `src.services.routing` exists or create it.
  - Add `get_eta(origin_lat, origin_lng, dest_lat, dest_lng) -> int (minutes)`:
    - Calls data provider (ORS).
    - Returns driving duration in minutes.

- **`WhatsAppService`**:
  - Update `handle_message` payload processing to detect `type="location"` messages.
  - Extract `lat`/`long` from the `location` object in the payload.

- **`TwilioService` (SMS)**:
  - Pass text messages to `LocationService.parse_location_from_text` to check for map links if no other command is matched.

### 3. User Flows

- **Employee Update (WhatsApp)**:
  - Sends location attachment -> Webhook -> `WhatsAppService` extracts coords -> `LocationService` updates DB -> Auto-reply "Tracking started".
- **Customer ETA**:
  - Customer says "Where are you?" -> LLM identifies intent -> Tool `GetETATool` ->
  - Finds active Job for customer -> Gets Employee ID -> Gets Employee Location ->
  - Calls `RoutingService.get_eta` -> Returns "10 mins away".
- **Business Query**:
  - Admin says "Locate John" -> Tool `LocateEmployeeTool` -> Returns map link/address.

## Work Packages

### Phase 0: Research & Scaffolding

- **WP00**: Sync & Research
  - **Goal**: Establish base from Spec 013 and verify API details.
  - **Tasks**:
    - [Manual] Pull/Merge changes from Spec 013 (or copy `RoutingService` and ORS adapter).
    - Verify Google Maps URL formats for regex parsing.
    - Verify ORS `/v2/directions` API response for ETA.

### Phase 1: Core Location Infrastructure

- **WP01**: Model & Location Service
  - **Goal**: Ability to store and retrieve user locations.
  - **Tasks**:
    - Migration: Add fields to `User`.
    - Implement `LocationService` (update, get, parse map links).
    - Unit tests for regex parsing of map links.

- **WP02**: ORS Routing Integration
  - **Goal**: Ability to calculate drive time.
  - **Tasks**:
    - Extend `RoutingService` (from 013) with `calculate_eta`.
    - Implement ORS client logic for Matrix/Directions if missing.
    - Add Mock implementation for tests.

### Phase 2: Messenger Integration

- **WP03**: Ingest Location Data
  - **Goal**: WhatsApp/SMS location messages update the DB.
  - **Tasks**:
    - Update `WhatsAppService` to handle `location` type messages.
    - Update `TwilioService` (SMS) to detect map links in text.
    - Connect both to `LocationService`.

### Phase 3: User Facing Features

- **WP04**: Tools & Logic
  - **Goal**: Expose data to LLM/Users.
  - **Tasks**:
    - Implement `LocateEmployeeTool` (Admin).
    - Implement `CheckETATool` (Customer).
      - Logic: Find active job by customer phone & time.
      - Logic: Calculate ETA.
    - Register tools with `ToolExecutor`.

---

**Step-by-step Execution Plan**:

1. Run `WP00` manually/interactively to sync 013 code.
2. Implement WP01 (Models).
3. Implement WP02 (Routing).
4. Implement WP03 (Ingest).
5. Implement WP04 (Tools).
