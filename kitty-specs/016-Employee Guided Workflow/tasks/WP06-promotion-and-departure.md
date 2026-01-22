# WP06: Promotion and Departure

## Goal

Implement role-based promotion (to manager) and the ability for employees to leave a business.

## Tasks

- [ ] **Role Management**: Add `role` field to `User` model and migrate.
- [ ] **Context Implementation**: Implement foundational "Employee Management" tool/context.
- [ ] **Promotion Tool**: Implement `PromoteUserTool` (restricted to Management context).
- [ ] **Dismissal Tool**: Implement `DismissUserTool` (restricted to Management context) for forceful departure.
- [ ] **Departure Tool**: Implement `LeaveBusinessTool` for employees to dissociate (self-departure).
- [ ] **RBAC Updates**: Ensure managers have appropriate permissions (mid-way between employee and owner).
- [ ] **Integration Tests**: Verify promotion, dismissal, and departure flows via chat.

## Acceptance Criteria

- Owner can promote or dismiss an employee via the management settings.
- Employee can leave the business via text.
- Changes are reflected in the database and access is revoked immediately for dismissed users.
