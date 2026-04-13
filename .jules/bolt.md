## 2026-01-22 - [ORM Caching Pitfalls]
**Learning:** Caching SQLAlchemy model instances (ORM objects) globally leads to "Shared Mutable State" and "DetachedInstanceError". When `session.expunge()` is used, objects become detached, breaking lazy loading and change tracking for consumers expecting attached objects.
**Action:** Always serialize ORM objects to plain dictionaries (DTOs) before caching. When retrieving from cache, reconstruct "transient" instances (e.g., `Service(**data)`) or return the dicts directly. This ensures each consumer gets a fresh, isolated copy of the data, preventing side effects and session binding issues.

## 2026-01-22 - [Missing Foreign Key Indexes]
**Learning:** Foreign Keys in SQLAlchemy models are NOT indexed by default (unlike Primary Keys). This can cause severe performance degradation (O(N) table scans) for common "get children" queries (e.g., `Job.customer_id`).
**Action:** Always verify if a ForeignKey is used in filtering or joining (especially from the "many" side). If so, explicitly set `index=True` in `mapped_column` definition.

## 2026-01-22 - [Indexing High-Cardinality Lookup Fields]
**Learning:** Frequent lookups on non-unique high-cardinality fields (like `Customer.phone`) cause full table scans if unindexed, degrading performance linearly with data growth.
**Action:** Identify fields used in "get by X" methods (e.g., `get_by_phone`) and add `index=True`. Benchmarking confirmed ~45% speedup even in small-scale in-memory tests.
