# Research Findings: Advanced Search

*Path: .kittify/missions/software-dev/templates/research-template.md*

**Feature**: Advanced Search
**Date**: 2026-01-15

## Existing Implementation Analysis

We have significant existing logic that can be reused:

### 1. Repositories

- **`CustomerRepository.search`**: Already implements robust filtering:
  - Text matching (Name, Phone, Address, City).
  - Phone normalization.
  - Query types: "scheduled" (joins Job), "added" (uses created_at).
  - Entity types: "lead" vs "customer".
  - Date filtering.
  - *Gap*: Geospatial filtering is currently done in Python (post-fetch). This is acceptable for <1k records but should be monitored.
- **`JobRepository.search`**: Matches `description` and `location`.
  - Supports status and date filtering.
- **`RequestRepository.search`**: Basic content matching.

### 2. Services

- **`GeocodingService`**: Already exists (`src/services/geocoding.py`) and uses Nominatim.
  - Returns `(lat, lon)`.
  - Used by `ToolExecutor` to resolve `center_address`.

### 3. Orchestration (The Gap)

- Currently, `ToolExecutor._execute_search` acts as the "Search Service".
- It handles:
  - Date parsing.
  - Geocoding resolution.
  - Dispatching to specific repositories based on `entity_type`.
  - formatting results (concatenating strings).
- **Goal**: Extract this logic into a dedicated `SearchService`.

## Unknown 1: Search Strategy

- **Decision**: Use standard SQL `ILIKE` / `OR` conditions (REUSE existing repository methods).
- **Rationale**:
  - Existing `CustomerRepository.search` already works well.
  - No need for external search engine yet.

## Unknown 2: Geocoding Provider

- **Decision**: Reuse existing `GeocodingService`.
- **Action**: No changes needed to the service itself, just import it into `SearchService`.

## Unknown 3: Architecture

- **Decision**: Extract `SearchService` as a specific Domain Service.
- **Rationale**:
  - `ToolExecutor` is becoming a "God Class".
  - Search logic needs to be unit testable in isolation from `ToolExecutor`.
  - Allows potential future REST API exposure.

## Unknown 4: Output Formatting

- **Problem**: `ToolExecutor` currently has hardcoded formatting.
- **Decision**: Implement `SearchService.format_results(results, detailed=True/False)`.
- **Structure**:
  - Concise: Name, Phone (e.g. `John Doe (555-0123)`)
  - Detailed: Name, Phone, Address, Details, Pipeline Stage, Last Interaction...
