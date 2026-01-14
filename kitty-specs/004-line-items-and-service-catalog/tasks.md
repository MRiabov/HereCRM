---
description: "Work package task list for Line Items & Service Catalog implementation"
---

# Work Packages: Line Items & Service Catalog

**Inputs**: Design documents from `/kitty-specs/004-line-items-and-service-catalog/`
**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (user stories), [data-model.md](data-model.md)

**Tests**: Testing requested for inference logic and job creation flows.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

---

## Work Package WP01: Foundation & Data Model (Priority: P1)

**Goal**: Establish the database schema and repository layer for Services and Line Items.
**Independent Test**: Database migrations apply successfully; Service and Line item models can be queried via repositories.
**Prompt**: `tasks/WP01-foundation-and-data-model.md`

### Included Subtasks

- [ ] T001 Implement `Service` model in `src/models.py`
- [ ] T002 Implement `LineItem` model and update `Job` model in `src/models.py`
- [ ] T003 [P] Create database migration for `Service` and `LineItem` tables
- [ ] T004 [P] Implement `ServiceRepository` in `src/repositories.py`
- [ ] T005 Update `JobRepository` to handle `LineItem` persistence and total value sync

### Implementation Notes

- Use SQLAlchemy for model definitions.
- `Job.value` should be kept in sync with the sum of its line items.
- Ensure `business_id` is present in `Service` for multi-tenancy.

### Parallel Opportunities

- Migrations and Repository implementation can start once models are defined.

### Dependencies

- None.

---

## Work Package WP02: Service Catalog Management (Priority: P2)

**Goal**: Implement the admin interface for managing the service catalog via a settings chat state.
**Independent Test**: User can enter `SETTINGS` state and successfully add/edit/list services.
**Prompt**: `tasks/WP02-service-catalog-management.md`

### Included Subtasks

- [ ] T006 Add Settings message templates to `src/assets/messages.yaml`
- [ ] T007 Implement `SETTINGS` state in `WhatsAppService` (`src/services/whatsapp_service.py`)
- [ ] T008 Implement CRUD operations for `Service` via `SETTINGS` menu commands
- [ ] T009 [P] Create `chat_utils.py` for generic menu/table rendering if needed

### Implementation Notes

- The `SETTINGS` state should restrict commands to catalog management.
- Use the message templates for consistent feedback.

### Parallel Opportunities

- Message templates and `chat_utils` can be handled in parallel.

### Dependencies

- WP01 (Repositories and Models needed).

---

## Work Package WP03: LLM & Line Item Inference (Priority: P1) 🎯 MVP

**Goal**: Update the LLM integration to intelligently infer line items from natural language input.
**Independent Test**: Simulated chat inputs correctly populate the `line_items` field in `AddJobTool`.
**Prompt**: `tasks/WP03-llm-and-inference.md`

### Included Subtasks

- [ ] T010 Update `AddJobTool` schema in `src/uimodels.py` to include `line_items`
- [ ] T011 Update `llm_client.py` system prompt and tool definition for line item extraction
- [ ] T012 Update `ToolExecutor` to process `line_items` during job creation
- [ ] T013 Implement unit price/quantity/total inference logic in LLM prompting or backend

### Implementation Notes

- The LLM should be instructed to look for quantities and prices.
- If only a total is provided, use the Service default price to infer quantity.
- If quantity is provided but no unit price, infer from total.

### Parallel Opportunities

- Schema updates and system prompt refinement.

### Dependencies

- WP01.

---

## Work Package WP04: UI & Reporting (Priority: P1)

**Goal**: Display line item breakdowns in job summaries and "Show Job" outputs.
**Independent Test**: "Show Job" output displays a clear table of line items with totals.
**Prompt**: `tasks/WP04-ui-and-reporting.md`

### Included Subtasks

- [ ] T014 Update "Show Job" output to display line items as a table/list
- [ ] T015 Update confirmation messages to summarize line items after job creation

### Implementation Notes

- Use fixed-width font or clear formatting for tables in WhatsApp/chat.
- Ensure totals are clearly shown.

### Parallel Opportunities

- Summary messages and "Show Job" display.

### Dependencies

- WP03 (Inferred items needed to display them).

---

## Work Package WP05: Refinement & Polish (Priority: P2)

**Goal**: Handle rounding, snapshotting, and edge cases.
**Independent Test**: Fractional quantities/prices round correctly to match totals; historical jobs remain stable after catalog changes.
**Prompt**: `tasks/WP05-refinement-and-polish.md`

### Included Subtasks

- [ ] T016 Handle rounding issues in unit price/quantity calculation
- [ ] T017 Validate snapshotting (historical jobs retain prices)
- [ ] T018 Add validation for edge cases (e.g., negative quantities, zero prices)

### Implementation Notes

- Ensure `LineItem` snapshots remain immutable once the job is created.

### Parallel Opportunities

- Rounding logic and validation checks.

### Dependencies

- WP04.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 & WP03 → WP04 → WP05.
- **Parallelization**: WP02 and WP03 can proceed mostly in parallel after WP01.
- **MVP Scope**: WP01, WP03, and WP04 are essential for the core line item functionality.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001       | Service Model | WP01 | P1 | No |
| T002       | LineItem Model | WP01 | P1 | No |
| T003       | Database Migration | WP01 | P1 | Yes |
| T004       | ServiceRepository | WP01 | P1 | Yes |
| T005       | JobRepository Update | WP01 | P1 | No |
| T006       | Message Templates | WP02 | P2 | Yes |
| T007       | Settings State | WP02 | P2 | No |
| T008       | CRUD Services | WP02 | P2 | No |
| T009       | Chat Utils | WP02 | P2 | Yes |
| T010       | AddJobTool Schema | WP03 | P1 | Yes |
| T011       | LLM Prompt Update | WP03 | P1 | Yes |
| T012       | ToolExecutor Update | WP03 | P1 | No |
| T013       | Inference Logic | WP03 | P1 | No |
| T014       | Show Job Table | WP04 | P1 | Yes |
| T015       | UI Summaries | WP04 | P1 | Yes |
| T016       | Rounding Logic | WP05 | P2 | Yes |
| T017       | Snapshot Validation | WP05 | P2 | No |
| T018       | Edge Case Validations | WP05 | P2 | Yes |
