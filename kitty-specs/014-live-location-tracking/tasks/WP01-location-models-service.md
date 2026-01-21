---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Foundation - Models & Location Service"
phase: "Phase 1 - Core Location Infrastructure"
lane: "doing"
dependencies: []
agent: "Antigravity"
shell_pid: "4073129"
history:
  - timestamp: "2026-01-21T10:21:37Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Foundation - Models & Location Service

## Objectives & Success Criteria

- Ability to store `latitude`, `longitude`, and `updated_at` on the `User` model.
- `LocationService` implemented as the source of truth for location updates and map link parsing.
- Unit tests validating that various Google/Apple Maps URLs are correctly parsed into coordinates.

## Context & Constraints

- Supporting docs: `kitty-specs/014-live-location-tracking/plan.md`, `data-model.md`.
- Coordinate format: Float (standard lat/lng).
- Timezone: Ensure `location_updated_at` uses UTC.

## Subtasks & Detailed Guidance

### Subtask T001 – Add location fields to User model

- **Purpose**: Persist employee location data.
- **Steps**:
  1. Open `src/models.py`.
  2. Add `current_latitude` (Float, nullable=True).
  3. Add `current_longitude` (Float, nullable=True).
  4. Add `location_updated_at` (DateTime, nullable=True).
- **Files**: `src/models.py`

### Subtask T002 – DB Migration

- **Purpose**: Apply schema changes to the database.
- **Steps**:
  1. Run `alembic revision --autogenerate -m "add_user_location_fields"`.
  2. Verify the migration file in `alembic/versions/`.
  3. Run `alembic upgrade head`.
- **Files**: `alembic/versions/*.py`

### Subtask T003 – Implement LocationService core

- **Purpose**: Provide a service layer for location CRUD.
- **Steps**:
  1. Create `src/services/location_service.py`.
  2. Implement `update_location(db: Session, user_id: int, lat: float, lng: float)`.
  3. Implement `get_employee_location(db: Session, user_id: int) -> Tuple[Optional[float], Optional[float], Optional[datetime]]`.
- **Files**: `src/services/location_service.py`

### Subtask T004 – Map Link Parsing logic

- **Purpose**: Extract coordinates from Google/Apple Maps shared URLs.
- **Steps**:
  1. Add `parse_location_from_text(text: str) -> Optional[Tuple[float, float]]` to `LocationService`.
  2. Use regex to find `maps.google.com`, `maps.app.goo.gl` or `apple.com/maps` patterns.
  3. Note: Some shortlinks might require a quick HEAD request to resolve the redirect if coordinates aren't in the slug (optional for MVP, regex on standard share links preferred).
- **Files**: `src/services/location_service.py`

### Subtask T005 – Location unit tests

- **Purpose**: Ensure parsing and service logic works.
- **Steps**:
  1. Create `tests/unit/test_location_service.py`.
  2. Test `update_location` updates DB correctly.
  3. Test `parse_location_from_text` with various URL formats (Google Maps mobile share, desktop link, Apple Maps share).
- **Files**: `tests/unit/test_location_service.py`

## Definition of Done Checklist

- [ ] All subtasks completed and validated.
- [ ] Database schema matches `models.py`.
- [ ] `LocationService` tests passing.
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Verify the regex for map links captures common share formats.
- Ensure `location_updated_at` is always updated on `update_location` calls.

## Activity Log

- 2026-01-21T10:21:37Z – antigravity – lane=planned – Prompt created.
- 2026-01-21T10:48:44Z – Antigravity – shell_pid=4035720 – lane=doing – Started implementation via workflow command
- 2026-01-21T11:00:46Z – Antigravity – shell_pid=4035720 – lane=for_review – Ready for review: Implemented location models, service, and comprehensive tests. All 12 unit tests passing.
- 2026-01-21T12:11:11Z – Antigravity – shell_pid=4073129 – lane=doing – Started review via workflow command
