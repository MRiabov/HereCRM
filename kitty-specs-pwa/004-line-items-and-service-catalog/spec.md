# Feature Specification: Line Items & Service Catalog

**Feature Branch**: `004-line-items-and-service-catalog`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description regarding jobber-like line items, service catalog management, and intelligent inference.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Intelligent Job Creation (Priority: P1)

As a user adding a job, I want the system to automatically infer line item details (quantity, unit price) from my natural language input so that I don't have to manually enter every field while still getting structured data for accounting.

**Why this priority**: This is the core data entry workflow. If this is friction-filled or inaccurate, the feature provides no value over plain text.

**Independent Test**: Can be tested by simulating chat inputs and verifying the resulting Job object structure.

**Acceptance Scenarios**:

1. **Given** a service "Window Clean" exists with default price $5, **When** user types "Add job for John, Window Clean, $50", **Then** system creates a job with 1 line item: "Window Clean", Quantity 10, Unit Price $5, Total $50.
2. **Given** a service "Window Clean" exists with default price $5, **When** user types "Add job for John, 12 windows for $50", **Then** system creates a job with 1 line item: "Window Clean" (or custom desc), Quantity 12, Unit Price ~$4.17, Total $50.
3. **Given** a service "Window Clean" exists, **When** user types "Add job for John, High Street 34, services: Window Clean" (no price), **Then** system uses default price ($5) and Quantity 1.
4. **Given** no matching service, **When** user types specific task "Fix Fence $100", **Then** system creates a generic line item "Fix Fence", Quantity 1, Total $100.

---

### User Story 2 - Manage Service Catalog (Priority: P2)

As an admin, I want to manage a catalog of services (Name, Default Price) via a dedicated "Settings" menu so that I can standardize pricing and prevent accidental changes during normal chat flow.

**Why this priority**: Essential for the inference logic to work (needs defaults), but P2 because initially one could survive with just ad-hoc items if needed.

**Independent Test**: Verification of the Settings UI state machine/menu flow.

**Acceptance Scenarios**:

1. **Given** user is in "Settings" mode/menu, **When** user selects "Add Service" and provides "Gutter Clean" @ $50, **Then** service is saved to catalog.
2. **Given** existing service, **When** user edits default price, **Then** new jobs use new price, existing jobs remain unchanged.
3. **Given** normal chat mode, **When** user tries to define service, **Then** system guides them to Settings menu (or treats it as a job note), protecting catalog integrity.

---

### User Story 3 - View Job Details with Line Items (Priority: P1)

As a user, I want to see the breakdown of line items when viewing a job/quote so I can verify what is being charged.

**Why this priority**: Essential for verification and transparency.

**Independent Test**: Visual verification of the "Show Job" output.

**Acceptance Scenarios**:

1. **Given** a job with multiple line items, **When** user asks to "Show job", **Then** output displays a table or list of items with Qty, Unit Price, and Total.

---

### Edge Cases

- **Service Deletion**: If a service is deleted from the catalog, existing historical jobs must preserve their line item data (snapshotting).
- **Ambiguous Input**: If input is "Clean for $50" and multiple "Clean" services exist, system should ask for clarification or default to a generic "Clean" item.
- **Micro-penny rounding**: When inferring unit price (e.g., 50 / 12), ensuring the total matches exactly $50 (checking for rounding errors).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow CRUD operations for a `Service` entity (Name, Default Price, Description) only via a dedicated Settings workflow.
- **FR-002**: `Job` entity MUST support a collection of `LineItem`s.
- **FR-003**: `LineItem` entity MUST store Description, Quantity, Unit Price, and Total Amount.
- **FR-004**: System MUST infer Quantity when Total Price and matched Service Default Price are known (Total / Default = Qty).
- **FR-005**: System MUST infer Unit Price when Total Price and Quantity are known (Total / Qty = Unit Price).
- **FR-006**: System MUST prioritize explicit user input over defaults (e.g., specific price overrides catalog default).
- **FR-007**: System MUST fallback to ad-hoc line items if no catalog service is matched.

### Key Entities

- **Service**: Catalog item. Attributes: `id`, `name`, `default_price`, `description`.
- **LineItem**: Instance on a job. Attributes: `description` (snapshot), `quantity`, `unit_price`, `total_price`, `service_id` (optional reference).
- **Job**: Existing entity, updated to include `line_items` list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Inference accuracy: 100% of "Total + Service" inputs correctly calculate Quantity.
- **SC-002**: Inference accuracy: 100% of "Total + Quantity" inputs correctly calculate Unit Price.
- **SC-003**: Data Integrity: 100% of historical jobs retain line item details even if Catalog Service is changed/deleted.
- **SC-004**: Usability: Users can add a standard job with line items in the same number of interactions as a plain text job (1 command).
