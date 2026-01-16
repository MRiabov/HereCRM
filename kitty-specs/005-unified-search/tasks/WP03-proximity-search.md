---
work_package_id: WP03
subtasks:
  - T009
  - T010
  - T011
  - T012
  - T013
lane: planned
---
# Work Package: Proximity Search

## Objective

Implement spatial search capability for Jobs and Customers.

## Context

Users need to find things "near X".

## Implementation Steps

1. **[T009] Geocoding Integration**
   - In `SearchService`, if `query.location` (or extracted location from query string) is present, call `self.geocoding_service.geocode(address)`.

2. **[T010] JobRepository Spatial Filter**
   - Update `JobRepository.search` in `src/repositories.py`.
   - Add logic: if `lat/long` and `radius` provided, filter results.
   - Use Haversine formula (implement helper in `src/utils.py` or similar) to filter in-memory if DB doesn't support it (SQLite).

3. **[T011] Update SearchService Location Handling**
   - Pass resolved coordinates to `JobRepository.search`.

4. **[T012] Generic Proximity**
   - If `query.entity_type` is missing but location is present, prioritize finding jobs and customers near that location.

5. **[T013] Integration Tests**
   - Add tests mocking the Geocoding API response. Create jobs with known Lat/Long. Verify filtering.

## Verification

- Run `pytest tests/test_search_service.py`
