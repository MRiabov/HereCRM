# Implementation Tasks: Geolocation & Maps Integration (WP08)

**Feature**: WhatsApp AI CRM
**Status**: In Progress / Partially Implemented
**Priority**: Medium - Enhancement
**Test**: `pytest tests/test_search_features.py` (Proximity tests)

## Description

Add location intelligence to the CRM. Access jobs and customers based on their physical location. This involves storing coordinates, supporting "near me" searches, and laying the groundwork for Google Maps integration.

## Tasks

- [x] **T032**: Add `latitude` and `longitude` columns to `Customer` and `Job` models.
- [x] **T033**: Update `SearchTool` to accept `radius`, `center_lat`, `center_lon`, `center_address`.
- [x] **T034**: Implement `haversine_distance` utility and spatial filtering logic in `BaseRepository` or specific repositories.
- [x] **T035**: Update `ToolExecutor` to pass spatial parameters to repositories.
- [ ] **T036**: Implement `GeocodingService` using OpenStreetMap (Nominatim) API to replace mocks.
- [ ] **T037**: Mock Geocoding in tests to avoid external API calls.
- [ ] **T038**: Implement "Get User Location" flow via WhatsApp Location messages (future).
- [ ] **T039**: Generate static map images for Job locations in confirmation messages (future).
