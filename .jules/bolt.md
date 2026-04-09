## 2026-01-22 - [ORM Caching Pitfalls]
**Learning:** Caching SQLAlchemy model instances (ORM objects) globally leads to "Shared Mutable State" and "DetachedInstanceError". When `session.expunge()` is used, objects become detached, breaking lazy loading and change tracking for consumers expecting attached objects.
**Action:** Always serialize ORM objects to plain dictionaries (DTOs) before caching. When retrieving from cache, reconstruct "transient" instances (e.g., `Service(**data)`) or return the dicts directly. This ensures each consumer gets a fresh, isolated copy of the data, preventing side effects and session binding issues.

## 2026-01-22 - [Missing Foreign Key Indexes]
**Learning:** Foreign Keys in SQLAlchemy models are NOT indexed by default (unlike Primary Keys). This can cause severe performance degradation (O(N) table scans) for common "get children" queries (e.g., `Job.customer_id`).
**Action:** Always verify if a ForeignKey is used in filtering or joining (especially from the "many" side). If so, explicitly set `index=True` in `mapped_column` definition.

## 2026-01-22 - [Missing Date and Status Indexes]
**Learning:** High-cardinality tables like `Jobs` often have "status" and "date" columns (e.g., `scheduled_at`, `status`) that are heavily used for filtering and sorting in dashboards and calendar views. These are often missed during initial schema design, leading to full table scans.
**Action:** Audit `Job` and `Request` models for `status` and timestamp columns. If used in `order_by` or range filters (e.g. `scheduled_at >= now`), explicitly add `index=True`.
