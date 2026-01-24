---
work_package_id: "WP01"
title: "Foundation & Data Model"
lane: "for_review"
dependencies: []
subtasks: ["T001", "T002", "T003"]
agent: "Antigravity"
shell_pid: "553005"
---

## Objective

Establish the foundation for Clerk authentication by installing dependencies, updating the configuration, and modifying the database schema to support Clerk IDs for Users and Businesses.

## Context

We are replacing the internal auth system for the PWA with Clerk. To do this, we need to link our internal entities (`User`, `Business`) to Clerk's entities (`User`, `Organization`) via external IDs.

## Subtasks

### T001: Add Dependencies

**Purpose**: Install necessary libraries for Clerk SDK, JWT handling, and cryptography.
**Steps**:

1. Edit `pyproject.toml`:
   - Add `clerk-backend-api` (latest stable).
   - Add `pyjwt` and `cryptography`.
2. Run `uv lock` (or `pip install` equivalent via the user's environment manager) to update lockfile (if applicable). *Note: User uses `uv` based on context rules.*

### T002: Database Migration

**Purpose**: persist `clerk_id` and `clerk_org_id` in the database.
**Steps**:

1. Modify `src/database/models.py` (or wherever `User` and `Business` are defined):
   - Add `clerk_id = Column(String, unique=True, nullable=True)` to `User`.
   - Add `clerk_org_id = Column(String, unique=True, nullable=True)` to `Business`.
2. Generate a new Alembic migration:
   - Run `alembic revision --autogenerate -m "add_clerk_ids"`.
   - Verify the generated script adds the columns and unique constraints.
3. Apply the migration `alembic upgrade head`.

### T003: Configuration Updates

**Purpose**: Expose Clerk credentials to the application.
**Steps**:

1. Modify `src/config.py` (Settings class):
   - Add `CLERK_SECRET_KEY: str`
   - Add `CLERK_PUBLISHABLE_KEY: str`
   - Add `CLERK_ISSUER: str` (e.g., `https://clerk.herecrm.com` or `https://adjusted-gopher-12.clerk.accounts.dev`)
   - Add `CLERK_JWKS_URL: str` (Automatic derived or explicit)
   - Ensure these are read from environment variables.

## Risks

- **Migration Locking**: Ensure migration doesn't lock tables for too long (though likely empty/small for dev).
- **Env Vars**: Make sure to document which env vars are needed for local dev (update `.env.example`).

## Activity Log

- 2026-01-24T21:13:11Z – Antigravity – shell_pid=553005 – lane=doing – Started implementation via workflow command
- 2026-01-24T21:17:24Z – Antigravity – shell_pid=553005 – lane=for_review – Ready for review: Established foundation with dependencies, data model updates (clerk_id/clerk_org_id), and configuration settings.
