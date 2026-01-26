---
FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/001-whatsapp-ai-crm/spec.md
---
# Feature Specification: WhatsApp AI CRM

**Feature**: WhatsApp AI CRM
**Status**: Draft
**Mission**: software-dev

## 1. Overview

A lightning-fast, text-first CRM living entirely within WhatsApp. It is designed for busy individuals and small teams to manage jobs, customers, and schedules using natural language commands. The system is multi-tenant, allowing business owners to onboard themselves and invite team members by phone number.

## 2. Functional Requirements

### 2.1. Onboarding & Auth

- **Self-Serve Creation**: The first time a phone number interacts with the bot, check if it belongs to an existing business. If not, create a new "Business" entity and make this user the Owner.
- **Team Management**: Business Owners can add other users to their business by sending a phone number.
- **Multi-Tenancy**: All data (jobs, customers, requests) is scoped to the Business. Users can only access data belonging to their Business.

### 2.2. Core Data Operations (LLM Powered)

The system must parse free-form messages to perform structured actions.

- **Add Job**:
  - Input: "add John, fix leaky faucet, 086123123" or "add John, 085123123, 50eur"
  - Action: Create Job record linked to Customer. Requires a price or job description.
  - Extraction: Name, Phone (optional), Location, Price, Description.

- **Add Lead/Client**:
  - Input: "add lead John, 085123123"
  - Action: Create Customer record ONLY. No Job is created.
  - Definition: A "Lead" is a Customer with no associated Jobs.
  - Extraction: Name, Phone, Address (Street, City, Country - default from settings if missing), Original Address Input, Description (stored in Customer details).
  
- **Schedule**:
  - Input: "schedule 085123123 at 14:00" or "schedule: john wanted his windows cleaned tomorrow 14:00"
  - Action: Update Job or Customer record with a time/date. Triggered if "schedule:" is used or a specific time in the future is supplied.
  
- **Store Request**:
  - Input: "add request: john wanted his windows cleaned tomorrow, 12 windows"
  - Input: "add request: john wanted his windows cleaned tomorrow, 12 windows"
  - Action: Store as a "Request" item with structured content and time. ONLY stored as a request if "add:" is explicitly followed by "request".
  - Extraction: Content, Client Details (if available), Time (default: "anytime").

### 2.3. Querying

- **Natural Language Search**:
  - Job querying:
    - "show jobs for customer with 085 123123"
    - "show jobs for customer with on High Street 44"
    - "who did we schedule on 14:00 today?"
    - "which job did we do on 10:00 today?"
    - "which job do we have on 10:00 today?"
    - "show jobs for today"
    - "show schedule for today"
    - "show completed jobs for today"
  - Customer querying:
    - "all customers named John"
    - "show all leads"
    - "show leads added today"
    - "show customers which jobs we did today".
    - "show all leads without jobs".
  - Request querying:
    - "show requests"
    - "Which requests are scheduled for saturday?"
  - **Geo-Search** (New):
    - "Search within 200m from me" (using User's location)
    - "Search within 1km of High Street 34, Dublin" (using Geoapify)
- **Output**: Formatted list of results (concise).

### 2.4. User Experience

- **Feedback**: Every mutating command (Add/Update/Delete) must return a **single-line confirmation**.
  - Example: `✔ Job added: John – High Road 34 – €50`
- **Undo/Edit**: The confirmation response must include options (buttons or text hints) to `Reply: undo | edit`.
- **Undo Action**: Reverts the last operation.
- **Edit Last Action**: Prompt the user to edit the last successful job, customer, or request. Example reply: `Edit the last job (John, 50$, No location). Type the job or customer details as you would before.`
- **Configurable Messaging**: All system-generated messages sent to customers must be configurable via a YAML file to allow easy text editing without code changes. These messages support variable interpolation using `{}` or `{{}}` syntax.

### 2.5. Security & Safety

- **Rate Limiting**: The system must include rate limiting on the public webhook to prevent denial-of-service and LLM credit exhaustion.
- **Input Validation**: All user inputs (webhook payload, LLM tool arguments) must be validated for length and expected format.
- **Prompt Injection Defense**: The system must be resilient against prompt injection attempts that try to subvert the LLM's tool-calling logic or access unauthorized data.
- **Safe State Updates**: Modifications to user preferences/settings must be restricted to an allowlist of approved keys.
- **Multi-Tenant Isolation**: Ensure all database queries are strictly scoped to the Business ID (Tenant Isolation).
- **Safe Error Handling**: API responses must not leak sensitive information (PII or technical stack details) in error messages.

## 3. Data Model (Conceptual)

- **Business**: [ID, Name, Settings (JSON, includes default_city, default_country), CreatedAt]
- **User**: [ID, Phone, Role (Owner/Member), BusinessID]
- **Customer**: [ID, Name, Phone, Street, City, Country, OriginalAddressInput, Latitude, Longitude, BusinessID]
- **Job**: [ID, CustomerID, Location, Value, Status, Latitude, Longitude, BusinessID]
- **Request**: [ID, Content, Status, BusinessID]
- **Appointment**: [ID, JobID, Time, BusinessID] (or field on Job)

## 4. User Scenarios

### Scenario 1: Zero-Friction Onboarding & Job Entry

1. **User** (new) sends: "Add: Sarah Smith, 555-0100, 123 Maple St, Window Cleaning $150"
2. **System**: Detects new user -> Creates Business -> Creates User -> Creates Customer (Sarah) -> Creates Job.
3. **System** replies: `✔ Job added: Sarah Smith – 123 Maple St – $150`
4. **User** replies: "undo"
5. **System** replies: `All changes reverted.`

### Scenario 1b: Edit Last

1. **User** sends: "Add: John, 50$"
2. **System** replies: `✔ Job added: John – No location – €50.0 (Reply 'undo' to revert)`
3. **User** sends: "edit last"
4. **System** replies: `Edit the last job (John, 50$, No location). Type the job or customer details as you would before.`

### Scenario 2: Team Collaboration

1. **Owner** sends: "Add user 555-0200"
2. **System** adds 555-0200 to Owner's business.
3. **Colleague** (555-0200) sends: "Show all jobs"
4. **System** returns list of jobs created by Owner.

### Scenario 3: Scheduling & Requests

1. **User** sends: "add request: Sarah wanted her windows cleaned, 12 windows"
2. **System** creates a Request for Sarah.
3. **System** replies: `✔ Request stored: Sarah wanted her windows cleaned`
4. **User** sends: "schedule Sarah at 2pm tomorrow"
5. **System** updates Sarah's latest job/record with appointment time 2026-01-14T14:00:00.
6. **System** replies: `✔ Scheduled Sarah Smith for Tomorrow 14:00`

## 5. Success Criteria

- **Parsing Accuracy**: >95% success rate extracting Name, Location, Price from standard "Add: ..." messages.
- **Latency**: End-to-end response time < 3 seconds for standard operations.
- **Isolation**: Users strictly cannot access data from other Businesses.
- **Simplicity**: No "registration forms" or explicit commands needed for onboarding.

## 6. Assumptions & Risks

- **WhatsApp API**: We assume using the existing a WhatsApp webhook setup.
- **LLM Cost**: Per-message LLM processing is acceptable for the business model.
- **Parsing**: If structured extraction fails, the system will respond with a "Sorry, we couldn't understand your request" message followed by a help guide, rather than storing it as a Request.
- **Phone Numbers**: Assumed to be unique identifiers for users.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/002-pipeline-progression/spec.md
---

# Feature Specification: Pipeline Progression Logic

**Feature Branch**: `002-pipeline-progression`  
**Created**: 2026-01-14  
**Status**: Draft  
**Input**: User description: "Implement a CRM pipeline with the following stages: Not Contacted (default for no jobs), Contacted (auto-triggered), Converted Once (1 job), Converted Recurrent (1+ jobs), Not Interested, and Lost. Users should be able to query counts per stage and filter customers by stage in search."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Pipeline Progression (Priority: P1)

As a CRM user, I want the system to automatically categorize my customers into pipeline stages based on their activity so that I can see the health of my sales funnel without manual updates.

**Why this priority**: Correct automatic categorization is the foundation of the pipeline logic. It ensures data consistency without user overhead.

**Independent Test**: Create a customer without jobs, verify they are "Not Contacted". Create a job for them, verify they become "Converted Once". Create a second job, verify they become "Converted Recurrent".

**Acceptance Scenarios**:

1. **Given** a new customer is added (e.g., "add lead John"), **When** I view the customer details, **Then** their stage is "Not Contacted".
2. **Given** a customer with no jobs, **When** a job is added (e.g., "add John, 50eur"), **Then** their stage automatically updates to "Converted Once".
3. **Given** a customer with one job, **When** another job is added, **Then** their stage automatically updates to "Converted Recurrent".

---

### User Story 2 - Pipeline Querying & Breakdown (Priority: P2)

As a business owner, I want to see a detailed breakdown of my pipeline, including both counts and customer details per stage, so that I can track progress and follow up with specific people.

**Why this priority**: This provides high-level visibility while enabling immediate action on specific customers.

**Independent Test**: Add customers to various stages, then run a query "show me our sales pipeline" and verify it returns a grouped list with customer details (Name, Address, Phone) for each stage.

**Acceptance Scenarios**:

1. **Given** multiple customers across different stages, **When** I ask "how many customers in which pipeline stages" or "show me our sales pipeline", **Then** the system returns a formatted list grouped by stage, showing the count and details (Name, Address, Phone) for customers in that stage.

---

### User Story 3 - Filtering by Stage in Search (Priority: P2)

As a user, I want to filter my customer list by pipeline stage so that I can focus on specific groups like "Leads" or "Lost" customers.

**Why this priority**: Directly requested by the user to improve search utility.

**Independent Test**: Search for "customers in stage Lost" and verify only customers with that status are returned.

**Acceptance Scenarios**:

1. **Given** customers in various stages, **When** I search "show me all Converted Once customers", **Then** only customers in that stage are listed.

---

### User Story 4 - Manual Stage Updates (Priority: P3)

As a user, I want to manually move customers to certain stages like "Not Interested" or "Lost" via natural language.

**Why this priority**: Some stages cannot be inferred automatically (e.g., a customer saying they are not interested).

**Independent Test**: Command "move John to Lost" and verify the stage updates correctly.

**Acceptance Scenarios**:

1. **Given** an active customer, **When** I send "mark John as Not Interested", **Then** their stage is updated to "Not Interested".

### Edge Cases

- **Mixed Automatic/Manual**: If a customer is manually marked as "Lost" but then a job is added, should they move to "Converted Once"? (Assumption: Yes, activity overrides terminal manual statuses unless otherwise specified).
- **Contacted Status**: How is "Contacted" triggered? (Assumption: Any incoming message from the customer or any outgoing message to them that isn't the first interaction).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a `pipeline_stage` field for each `Customer`.
- **FR-002**: Pipeline stages MUST include: `Not Contacted`, `Contacted`, `Converted Once`, `Converted Recurrent`, `Not Interested`, `Lost`.
- **FR-003**: System MUST set default stage to `Not Contacted` for new customers without jobs.
- **FR-004**: System MUST automatically update stage to `Converted Once` when the first job is created for a customer.
- **FR-005**: System MUST automatically update stage to `Converted Recurrent` when the second or subsequent job is created.
- **FR-006**: System MUST automatically update stage to `Contacted` upon communication interaction (needs concrete definition in implementation).
- **FR-007**: System MUST allow manual stage updates via LLM commands for terminal stages like `Not Interested` and `Lost`.
- **FR-008**: System MUST support querying the pipeline to show counts per stage AND detailed lists of customers (Name, Address, Phone) within each stage.
- **FR-009**: System MUST support filtering customers by `pipeline_stage` in search queries.

### Key Entities

- **Customer**: Updated to include `pipeline_stage` (ENUM or String).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can get a pipeline breakdown in under 3 seconds.
- **SC-002**: 100% of customers are automatically transitioned to "Converted Once" upon their first job creation.
- **SC-003**: Search results accurately filter by stage with 100% precision.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/003-automatic-customer-messaging/spec.md
---

# 003 Automatic Customer Messaging

## Goal

Enable businesses to schedule and send automated messages to customers via WhatsApp (default) or SMS (configurable) based on specific triggers and events.

## Problem Statement

Currently, businesses have to manually message customers for routine updates. There is a need for an automated system where messages are triggered by specific events (e.g., "On my way", "Job booked", "Job scheduled for today").

## Functional Requirements

1. **Multi-Channel Support**:
   - Primary: WhatsApp.
   - Secondary: SMS (Configurable option).
2. **Event-Based Triggers**:
   - Provide a generic interface/event bus to subscribe to important business events.
   - Specific Triggers:
     - **On My Way**: Triggered by business user (e.g., via chat command).
     - **Job Opening/Booking**: Triggered when a new job is created/booked.
     - **Job Scheduling**: Triggered when a job is scheduled.
     - **Quotes**: Triggered when a quote is generated (future integration).
     - **Daily Schedule**: Automated "Scheduled Today" messages.
3. **Architecture**:
   - Async message queue for processing and sending messages.
   - Decoupled event subscribers.

## User Interface

- Business users trigger ad-hoc messages (like "On my way") via the CRM interface (WhatsApp/Chat).
- Configuration for enabling/disabling SMS vs WhatsApp.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/004-line-items-and-service-catalog/spec.md
---

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

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/005-unified-search/spec.md
---

# Feature Specification: Advanced Search

**Feature Branch**: `005-unified-search`  
**Created**: 2026-01-15  
**Updated**: 2026-01-17 (Post-merge of 002, 004)  
**Status**: Draft  
**Input**: User description: "Implement a central Search functionality in the application. It should use an LLM to automatically identify what is being searched for (job, request, customer) and the fields effectively. support 'detailed' keyword. maintain existing formatting. Handle edge cases. Support Proximity search using OpenStreetMap. It should be a unified SearchService."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Flexible Entity Search (Priority: P1)

Users need to search for Jobs, Customers, or Requests using natural language without specifying the entity type explicitly, allowing for a fluid conversational experience.

**Why this priority**: Core value proposition of "unified" search - removing friction of specific commands.

**Independent Test**: Can be tested by sending varied search queries ("Find John", "Show jobs for John", "Requests about windows") and verifying correct entities are returned.

**Acceptance Scenarios**:

1. **Given** one or more customers named "John Doe" exist, **When** user sends "Find John", **Then** system returns all matching Customer records for John Doe.
2. **Given** one or more jobs associated with "John Doe" exist, **When** user sends "Show jobs for John", **Then** system returns all associated Job records.
3. **Given** one or more requests containing "leaky faucet" exist, **When** user sends "search for leaky faucet", **Then** system returns all matching Request records.

---

### User Story 2 - Proximity Search (Priority: P1)

Users need to find customers or jobs near a specific location or their own location to optimize routing and logistics.

**Why this priority**: High business value for routing and planning field work.

**Independent Test**: Create entities at known locations, run "search within X km of Y", verify inclusion/exclusion.

**Acceptance Scenarios**:

1. **Given** a customer at "High St, Dublin" and one in "Cork", **When** user sends "Show customers within 5km of High St, Dublin", **Then** system returns only the Dublin customer.
2. **Given** a user location is provided (simulated), **When** user sends "Jobs near me", **Then** system uses user location as center point for proximity search.
3. **Given** an invalid address, **When** user searches near it, **Then** system gracefully informs about geocoding failure or suggests correction.

---

### User Story 3 - Detailed View (Priority: P2)

Users need to see full details of a record on demand, while keeping the default view concise to avoid screen clutter.

**Why this priority**: Balances need for quick scanning (concise) with need for deep dive (detailed).

**Independent Test**: Search with and without "detailed" keyword, compare output length/fields.

**Acceptance Scenarios**:

1. **Given** a customer "Jane", **When** user sends "Show Jane", **Then** system returns a concise summary (Name, Phone, maybe Address).
2. **Given** a customer "Jane", **When** user sends "Show Jane detailed", **Then** system returns full record (Name, Phone, Address, Notes, History).

---

### User Story 4 - Complex Filtering (Priority: P3)

Users need to filter by specific attributes like phone number, date, or status.

**Why this priority**: Enhances power user capabilities and precise retrieval.

**Independent Test**: Search by phone substring, date ranges, or status.

**Acceptance Scenarios**:

1. **Given** multiple customers, **When** user searches by partial phone number "085", **Then** system returns all matching customers.
2. **Given** jobs in different statuses, **When** user asks "Show pending jobs", **Then** system returns only jobs with status 'PENDING'.
3. **Given** jobs created on different dates, **When** user asks "Show jobs created last week", **Then** system returns jobs with `created_at` within the last 7 days.
4. **Given** jobs with and without schedules, **When** user asks "Show unscheduled jobs", **Then** system returns jobs where `scheduled_time` is null.
5. **Given** jobs scheduled for various dates, **When** user asks "Show jobs for next month" or "Show jobs on Jan 25th", **Then** system returns jobs with `scheduled_time` matching the parsed date range.
6. **Given** customers in various pipeline stages (from Feature 002), **When** user asks "Show lost customers", **Then** system returns customers with `pipeline_stage == 'lost'`.
7. **Given** a service catalog (from Feature 004), **When** user asks "Search for customers for whom we performed Window Cleaning", **Then** system returns customers for whom we performed those services.
8. **Given** a service catalog (from Feature 004), **When** user asks "Search for jobs for where we performed Window Cleaning", **Then** system returns jobs for those services.

## Edge Cases

- **Large Result Sets**: If "Show all jobs" returns 100 items, system should truncate or paginate to avoid WhatsApp message limits.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a unified `SearchService` that accepts a natural language query string.
- **FR-002**: System MUST use an LLM (via `LLMClient`) to interpret the query intent (Target Entity: Customer/Job/Request/Service/All) and extract filter parameters (Name, Phone, Location, Status, PipelineStage, CreatedAt, ScheduledTime, "Detailed" flag).
- **FR-003**: System MUST support "Proximity Search" by geocoding a reference address (using Geoapify) and filtering entities validation logic (within X km/meters).
- **FR-004**: System MUST support an explicit boolean `detailed` flag in the search context; if true, the output formatter renders extended data (e.g., job line items, full customer notes).
- **FR-005**: System MUST maintain current "concise" formatting (summary view) by default, preserving changes introduced by Feature 002 (stages) and 004 (line items).
- **FR-006**: System MUST return grouped results if multiple entity types match (e.g., "Results for 'John': 1 Customer, 2 Jobs").
- **FR-007**: System MUST handle pagination or truncation for > 10 results to fit WhatsApp constraints.
- **FR-008**: System MUST support searching the Service Catalog specifically (Entity: Service).
- **FR-009**: System SHOULD support searching Message Logs (from Feature 003) if available in the database.

### Key Entities

- **SearchService**: Core domain service handling orchestration.
- **SearchRequest**: Value object representing the parsed intent (target entity, filters, flags).
- **GeocodingService**: (Wrapper around OSM) to convert Address -> Lat/Long.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Proximity searches return results within requested radius with 90% accuracy (dependent on OSM data).
- **SC-002**: "Detailed" view requests trigger full data display 100% of the time.
- **SC-003**: Search queries returning < 5 items render in under 3 seconds.
- **SC-004**: Ambiguous queries (e.g., common names) return results from multiple categories if applicable, rather than failing.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/006-professional-invoices/spec.md
---

# Feature Specification: Professional Invoices

**Feature Branch**: `006-professional-invoices`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User wants professional PDF invoices sent via WhatsApp/SMS/Email, preventing duplicates, defaulting to the last job.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send Invoice for Last Job (Priority: P1)

As a user, I want to quickly generate and send an invoice for the most recent job completed for a customer so that I can get paid without manual data entry.

**Why this priority**: This is the primary "happy path" workflow.

**Independent Test**: Simulate chat command "Send invoice to [Customer]" and verify PDF generation + message output.

**Acceptance Scenarios**:

1. **Given** a customer "John" with a completed job ($100, pending invoice), **When** user says "Send invoice to John", **Then** system finds the job, generates a professional PDF, saves it, and returns a WhatsApp message with the PDF and/or link.
2. **Given** multiple customers named "John", **When** user says "Send invoice to John", **Then** system asks for clarification or lists options.
3. **Given** no recent job for "John", **When** user says "Send invoice to John", **Then** system responds that no billable job was found.

---

### User Story 2 - Prevent Duplicate Invoices (Priority: P2)

As a business owner, I want to be warned if I try to send an invoice for a job that has already been invoiced so that I don't look unprofessional or confuse the customer.

**Why this priority**: Essential for business professionalism and data integrity.

**Independent Test**: Attempt to generate an invoice twice for the same job.

**Acceptance Scenarios**:

1. **Given** a job that already has an associated Invoice record, **When** user tries to "Send invoice" again, **Then** system warns "Invoice already exists sent on [Date]" and asks for confirmation to resend or regenerate.

---

### User Story 3 - Professional PDF Styling (Priority: P2)

As a business owner, I want the invoices to look professional (clean layout, logo placeholders) so that my business looks reputable.

**Why this priority**: User explicitly requested "very professional" look.

**Independent Test**: Visual inspection of the generated PDF.

**Acceptance Scenarios**:

1. **Given** a job with line items, **When** invoice is generated, **Then** the PDF contains Business Name, Customer Details, Line Item Table, Total, and Date, formatted cleanly (e.g., HTML/CSS template converted to PDF).

---

### User Story 4 - Custom Payment Link (Priority: P2)

As a business owner, I want to add my own payment link (Stripe, PayPal, etc.) to my invoices so that my customers can pay me easily online.

**Why this priority**: Improves cash flow for the business and convenience for the customer.

**Independent Test**: Configure a payment link for a business, generate an invoice, and verify the link appears in the PDF and message.

**Acceptance Scenarios**:

1. **Given** a business with a configured payment link "<https://stripe.com/pay/abc>", **When** an invoice is generated, **Then** the PDF contains a "Pay Now" button/link and the WhatsApp message includes the link.
2. **Given** a business with NO payment link configured, **When** an invoice is generated, **Then** no payment button appears in the PDF and no link is sent in the message.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be able to identify the target customer from natural language (Name, Phone, or Address) using the existing Search/Lookup logic.
- **FR-002**: System MUST identify the *last performed job* for the target customer to invoice by default.
- **FR-003**: System MUST verify if an `Invoice` already exists for the selected Job. If yes, return a warning before proceeding.
- **FR-004**: System MUST generate a PDF file from the Job data ensuring professional formatting.
- **FR-005**: System MUST store the generated PDF using a persistent storage mechanism.
- **FR-006**: System MUST Create an `Invoice` entity linked to the Job upon successful generation.
- **FR-007**: System MUST be able to return a "Send" action (returning the link/file path to the chat interface).
- **FR-008**: System MUST allow a Business to store a `payment_link` in their settings.
- **FR-009**: System MUST include a prominent "Pay Now" button in the PDF invoice if `payment_link` is configured.
- **FR-010**: System MUST include the `payment_link` in the WhatsApp/SMS message sent along with the invoice.
- **FR-011**: System MUST allow configuring the `payment_link` via the conversational Settings interface.

### Key Entities

- **Invoice**: New entity.
  - `id`: Unique Identifier
  - `job`: Reference to Job (One-to-One)
  - `created_at`: Timestamp
  - `file_location`: Location/Link to the file
  - `status`: Status of the invoice (e.g., DRAFT, SENT)
  - `payment_link`: Snapshot of the payment link used for this invoice.
- **Job**: Existing entity.
- **Business**: Existing entity.
  - `payment_link`: URL for customer payments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Efficiency: User can generate an invoice in **1 command** ("Send invoice to X") for the common case.
- **SC-002**: Safety: System warns **100% of the time** if an invoice already exists for the job.
- **SC-003**: Quality: Generated PDF allows for clear reading of line items and totals (Visual check).
- **SC-004**: Performance: PDF generation and delivery action takes under **60 seconds**.

## Tax Calculation

### Overview

Invoices must accurately calculate and display applicable taxes using the Stripe Tax API. The system will query Stripe Tax to determine the correct tax rates based on the business location, customer location, and service type.

### Business Settings

Businesses can configure how taxes are applied to their pricing:

- **Tax Application Mode**: Toggle between "Tax Included" and "Tax Added"
  - **Tax Included**: The price shown to customers already includes tax (tax is calculated backwards from the total)
  - **Tax Added**: Tax is calculated and added on top of the stated price
  - This setting is stored in the `Business` model as `tax_mode` field

### Tax Functional Requirements

- **FR-TAX-001**: System MUST integrate with Stripe Tax API to calculate accurate tax amounts
- **FR-TAX-002**: System MUST respect the business's `tax_mode` setting when calculating totals
- **FR-TAX-003**: System MUST display tax breakdown on invoices (tax rate, tax amount, subtotal, total)
- **FR-TAX-004**: System MUST handle tax calculation errors gracefully (fallback to 0% tax with warning)
- **FR-TAX-005**: System MUST cache tax calculations to avoid redundant API calls for identical line items

### Tax Display

Invoices must clearly show:

- Subtotal (before tax for "Tax Added" mode, or net amount for "Tax Included" mode)
- Tax rate(s) applied
- Tax amount
- Grand total

## Assumptions & Dependencies

- "Sending" initially means returning the link/file to the chat context.
- The system will use a storage provider capable of retaining files permanently.
- Stripe Tax API credentials are configured and valid.
- Business and customer location data is accurate for tax calculation purposes.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/007-customer-import-export/spec.md
---

# Feature Specification: Customer Data Import & Export

**Feature Branch**: `007-customer-import-export`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User description: "Implement customer import and export functionality with a dedicated screen. Key features: LLM-powered natural language export queries, flexible import parsing with strict validation (preferring imported data for duplicates), support for CSV/JSON/Excel formats, and smart header mapping. Imports should include customer details and associated jobs. Safety mechanisms must prevent database corruption."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smart Data Import (Priority: P1)

Users need to bulk import customer and job data from various legacy formats (CSV, Excel, JSON) with different column names, without manually reformatting their files.

**Why this priority**: Essential for onboarding new users who bring data from other systems. Reduces friction and manual data entry.

**Independent Test**: Provide a CSV with non-standard headers (e.g., "Client Name" instead of "name") and verify the system correctly maps and imports the data without errors.

**Acceptance Scenarios**:

1. **Given** a CSV file with "Client Phone" and "Client Name" headers, **When** user uploads it for import, **Then** system intelligently maps these to "phone" and "name" and imports records.
2. **Given** an import file contains a customer that already exists (match by phone/email), **When** import functions runs, **Then** system updates the existing customer details with new data and adds any new jobs from the file.
3. **Given** a malformed file (e.g., missing required fields for some rows), **When** user attempts import, **Then** system rejects the *completely* and provides specific error feedback.

---

### User Story 2 - Natural Language Data Export (Priority: P1)

Users need to export specific subsets of their data for reporting or external use by describing what they want in plain English.

**Why this priority**: Empowers non-technical users to access their data without constructing complex database queries.

**Independent Test**: Request "Export all customers with pending jobs from last month" and verify the resulting CSV/Excel file contains exactly those records.

**Acceptance Scenarios**:

1. **Given** a request "Export customers in Dublin added last week", **When** user submits export request, **Then** system generates a downloadable file with only matching customers and their data.
2. **Given** a request specifies "as JSON", **When** export is generated, **Then** the file format is valid JSON.

---

### User Story 3 - Dedicated Data Management Screen (Priority: P2)

Users need a safe, dedicated area to perform these sensitive bulk operations to strictly separate them from daily operational workflows.

**Why this priority**: Prevents accidental data modification and reduces UI clutter on the main dashboard.

**Independent Test**: Navigate to the new "Data Management" route and verify access to Import/Export tools.

**Acceptance Scenarios**:

1. **Given** the user is on the dashboard, **When** they navigate to "Data Management", **Then** they see clear options for "Import" and "Export" with recent history or logs.

---

## Edge Cases

- **Large File Imports**: System should enforce reasonable file size limits (e.g., 20MB) to prevent timeouts.
- **Ambiguous Header Mapping**: If LLM cannot confidently map headers, the system should prompt the user for clarification or fail safely rather than guessing wrong.
- **Partial Failures**: Import MUST be atomic. If row 99 of 100 fails validation, the entire batch of 100 MUST be rolled back.
- **Export Volume**: If an export query matches >10,000 records, system should warn the user or stream the response to prevent memory exhaustion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated "Data Management" view separate from the main dashboard.
- **FR-002**: System MUST support importing data from CSV, JSON, and Excel (.xlsx) formats.
- **FR-003**: System MUST use an LLM to analyze upload file headers and map them to the internal `Customer` and `Job` schema.
- **FR-004**: Import process MUST be atomic; if any record in a batch creates a validation error, the entire batch is rejected.
- **FR-005**: System MUST automatically create new `Customer` records if they do not exist.
- **FR-006**: System MUST update existing `Customer` records (matched by unique identifier like phone/email) with imported data (overwrite) and append new `Job` records.
- **FR-007**: System MUST support Natural Language querying for exports (e.g., "Export customers with completed jobs").
- **FR-008**: System MUST support exporting to CSV, JSON, and Excel formats.
- **FR-009**: System MUST validate strict data integrity types (e.g., dates are valid dates, prices are non-negative) before attempting database write.

### Key Entities

- **ImportJob**: Represents a bulk import attempt (Status: Pending, Processing, Completed, Failed; Logs).
- **ExportRequest**: Represents a user's request to extract data (Query, Format, Status).
- **DataMapping**: The schema map generated by the LLM (Source Column -> Target Field).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of standard CSV imports with non-matching but semantically similar headers are mapped correctly without user intervention.
- **SC-002**: 100% of invalid imports result in zero database changes (Atomic Transaction guarantee).
- **SC-003**: Users can successfully filter export data using natural language queries with 90% intent accuracy.
- **SC-004**: System handles files up to 10MB or 5000 records within 30 seconds.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/008-intelligent-product-assistant/spec.md
---

# Feature Specification: Intelligent Product Assistant & Documentation

**Feature Branch**: `008-intelligent-product-assistant`  
**Created**: 2026-01-18  
**Status**: Draft  
**Input**: User documentation and a LLM RAG assistant. "how do I add a lead?", "why did my last prompt fail", "what can I do to use you better?". Access to last 5 messages/tool calls.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - "How-To" Guidance (Priority: P1)

As a user, I want to ask "How do I add a lead?" or "How do I schedule a job?" so that I can learn how to use the CRM features without reading a long manual.

**Why this priority**: Essential for onboarding and user retention. Reduces friction for new users.

**Independent Test**: Can be tested by sending "How do I add a lead?" and verifying the response contains instructions from the manual.

**Acceptance Scenarios**:

1. **Given** a product manual exists, **When** user asks "How do I add a lead?", **Then** assistant responds with the specific steps from the manual.
2. **Given** a product manual exists, **When** user asks about a featue not in the manual, **Then** assistant politely states it doesn't know and suggests checking available commands.

---

### User Story 2 - Interaction Troubleshooting (Priority: P1)

As a user, I want to ask "Why did my last prompt fail?" or "Why didn't you add that job?" so that I can understand what went wrong and how to format my request better.

**Why this priority**: Crucial for building trust and helping users correct their input patterns.

**Independent Test**: Can be tested by intentionally sending an ambiguous message (e.g., "Add job") followed by "Why did that fail?".

**Acceptance Scenarios**:

1. **Given** the last user message resulted in a parsing error or clarification request, **When** user asks "Why did it fail?", **Then** assistant explains the missing information (e.g., "The message didn't contain a customer name").
2. **Given** the last 5 messages are available, **When** user asks "What can I do to use you better?", **Then** assistant provides suggestions based on recent interaction patterns and the manual.

---

### User Story 3 - Capability Discovery (Priority: P2)

As a user, I want to ask "What can I do?" or "Show me what you can do" so that I can explore the system's capabilities.

**Why this priority**: Helps users discover features they haven't used yet.

**Independent Test**: Can be tested by asking "What can you do?" and verifying it lists key CRM functions (leads, jobs, search, etc.).

**Acceptance Scenarios**:

1. **Given** a product manual exists, **When** user asks "What can I do?", **Then** assistant provides a high-level summary of supported actions (Adding leads, scheduling jobs, searching, etc.).

---

### Edge Cases

- **History empty**: If a new user asks "Why did my last prompt fail?", assistant should handle the lack of history gracefully (e.g., "I don't have enough context yet. Try asking how to do something specific!").
- **Manual missing**: System should have a fallback help message if the RAG document is unavailable.
- **Ambiguous failure**: If the LLM itself failed (e.g., API error), the assistant should explain that it was a system error rather than a user input error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an intelligent assistant accessible via a tool call (triggered by keywords like "help", "how to", "why did...").
- **FR-002**: Assistant MUST use RAG or prompt-injection over a markdown documentation file (`manual.md`).
- **FR-003**: System MUST fetch the last 5 messages (user and assistant) and their associated metadata (tool calls, error logs) from the database to provide context.
- **FR-004**: Assistant MUST be able to explain failed parsing attempts (when `LLMParser` returns `error_unclear_input` or a clarification request).
- **FR-005**: Assistant MUST adapt response length and formatting to the active channel (SMS, Email, WhatsApp, etc.), respecting a configurable integer max/desired length for each channel (e.g., brief for SMS, detailed for Email).
- **FR-006**: Assistant MUST prioritize information from the product manual for "how-to" queries.
- **FR-007**: System MUST provide a `HelpTool` that triggers this assistant flow.

### Key Entities *(include if feature involves data)*

- **Message**: Represents previous interactions stored in the database, including role (user/assistant), body, and `log_metadata` (containing tool call details).
- **Product Manual**: A markdown file(s) containing feature descriptions and usage guides.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Assistant correctly identifies the cause of 4 out of 5 common parsing failures in test sets.
- **SC-002**: Answers to "How-To" questions are strictly derived from the manual (no hallucination of unsupported features).
- **SC-003**: Help responses are delivered within 2 seconds of the user's request.
- **SC-004**: User "re-try" success rate increases (users successfully format requests after being told why they failed).

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/009-multi-channel-communication/spec.md
---

# Feature Specification: Multi-channel Communication

**Feature Branch**: `009-multi-channel-communication`  
**Created**: 2026-01-19  
**Status**: Draft  
**Input**: User description: "Add support for SMS (Twilio), Email (Postmark), and Generic Webhook channels. Includes User model refactoring for identity management and channel-specific configuration with auto-confirmation logic."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-channel Engagement (Priority: P1)

A business can engage with customers across WhatsApp, SMS, and Email, using the most appropriate channel for each customer while maintaining a unified profile.

**Why this priority**: Core value proposition of the feature. Expands market reach beyond WhatsApp-dominant regions.

**Independent Test**: Can be tested by sending/receiving messages on all 3 channels to the same "User" entity.

**Acceptance Scenarios**:

1. **Given** a customer with a valid phone number, **When** the business answers via SMS, **Then** the message is sent via Twilio and the customer receives it.
2. **Given** a customer with a valid email, **When** the business answers via Email, **Then** the message is sent via Postmark and the customer receives an email.
3. **Given** a unified user profile, **When** messages come from different channels linked to that profile, **Then** they appear in the same conversation history (or are reasonably linked).

---

### User Story 2 - Cost-Efficient Confirmation (Priority: P1)

In expensive channels (SMS/Email), the system minimizes back-and-forth by auto-confirming pending actions if the user doesn't object.

**Why this priority**: Essential for cost control and UX on higher-latency/cost channels.

**Independent Test**: Verify the "45-second rule" logic in the state machine.

**Acceptance Scenarios**:

1. **Given** a pending tool action (e.g., "Create Job") on an SMS channel, **When** 45 seconds pass without user input, **Then** the action is automatically executed.
2. **Given** a pending tool action on SMS, **When** the user sends "Cancel" within 45 seconds, **Then** the action is aborted and no execution occurs.
3. **Given** a standard WhatsApp channel (default config), **When** a tool action is pending, **Then** it waits indefinitely for explicit confirmation (preserving existing behavior).

---

### User Story 3 - Integrations via Webhook (Priority: P2)

External systems (e.g., Zapier, Contact Forms) can inject messages or leads into the CRM via a generic webhook.

**Why this priority**: Enables flexibility and "catch-all" integration support.

**Independent Test**: Post a JSON payload to the new webhook endpoint and verify a registered message/lead.

**Acceptance Scenarios**:

1. **Given** a valid JSON payload sent to the generic webhook, **When** received, **Then** a new message/request is created in the system.
2. **Given** a payload with a known email/phone, **When** received, **Then** it is successfully linked to the existing user (if implemented) or creates a new one.

### Edge Cases

- **Concurrent Channel Usage**: User sends an SMS and an Email simultaneously. System should handle race conditions cleanly (likely sequential processing).
- **Identity Merging**: User starts on SMS, then emails. System might initially treat them as separate users unless an explicit "merge" or "link" feature exists (Out of scope for this MVP? Assumed separate unless matching handle provided). *Assumption: Matching by exact phone or email if provided.*
- **Invalid Channel Config**: System attempts to send SMS but Twilio config is missing. Should fail gracefully and log error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support **Twilio** for inbound/outbound SMS.
- **FR-002**: System MUST support **Postmark** for inbound/outbound Email (including threading logic).
- **FR-003**: System MUST provide a **Generic Webhook** endpoint accepting a standard JSON schema for inbound messages.
- **FR-004**: System MUST refactor the `User` model to use an **Integer ID** as the primary key, supporting `phone_number` and `email` as optional, unique, indexable fields.
- **FR-005**: System MUST support **per-channel configuration defaults** (YAML-based), specifically for `auto_confirm` behavior and timeouts.
- **FR-006**: System MUST implement an **Auto-Confirmation Strategy** where pending actions on configured channels (SMS/Email) execute automatically after a configurable timeout (default 45s) if no cancellation is received.
- **FR-007**: System MUST support **WhatsApp** via the existing Meta API integration (preserving current functionality).
- **FR-008**: System MUST allow configuring the "Max Message Length" or "conciseness" per channel (e.g., compact for SMS, standard for Email).

### Key Entities

- **User**: Refactored to have Integer ID, `email` (nullable), `phone` (nullable, but one is required).
- **ChannelConfig**: (Concept/File) Stores settings like `provider`, `auto_confirm_enabled`, `auto_confirm_timeout`, `max_length` for each channel type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: SMS messages are sent/received via Twilio with < 2s internal processing latency.
- **SC-002**: Email messages are sent/received via Postmark with threading headers correctly maintained.
- **SC-003**: "Auto-confirm" actions execute successfully after the timeout window (±5s accuracy) without user intervention.
- **SC-004**: System handles concurrent inputs from different channels for the same user without data corruption.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/010-conversational-billing/spec.md
---

# Feature Specification: Conversational Customer Billing & Addons

**Feature Branch**: `010-conversational-billing`  
**Created**: 2026-01-20  
**Status**: Draft  
**Input**: User description: "customer billing: in 'settings'->'billing settings' users can see their a) billing status b) an option to add employees (expand seats, for a price) c) an option to add addons. Addons expand functionality like 1. Employee management addon 2. Customer campaign messaging addon 3. Etc. configurable via yaml. Tools require a 'scope'. Users can request 'add [addon name] to my subscription' which prompts payment. Payment procedure: 1. User requests pay. 2. App calculates total. 3. App sends subtotal and link. 4. Stripe link. 5. Automatic registration."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Billing Status (Priority: P1)

As a business owner, I want to check my current subscription status, including seats and active addons, by typing "billing" or "billing settings" in the chat, so that I know what I'm paying for.

**Why this priority**: Essential for visibility and entry point to other billing actions. Without this, users cannot see what they have or need.

**Independent Test**: Can be tested by simulating "billing" command for users with different states (free tier, paid seats, active addons) and verifying the response correctly outlines their current package.

**Acceptance Scenarios**:

1. **Given** a user is in "idle" or "settings" state, **When** they type "billing", **Then** the system enters BILLING state and replies with a summary of their current plan, number of seats, and active addons.
2. **Given** a user with 5 seats and "Campaign Messaging" addon, **When** they request billing status, **Then** the response explicitly lists "5 Seats" and "Campaign Messaging: Active".

---

### User Story 2 - Automated Payment & Provisioning Flow (Priority: P1)

As a user, I want to pay for upgrades via a secure link and have the features enabled immediately, so that I don't have to contact support or leave the chat context to upgrade.

**Why this priority**: Critical path for revenue. If users can't pay or features don't unlock, the upsell feature is useless.

**Independent Test**: Can be tested by mocking the payment generation and webhook receipt, verifying that the database updates the business's entitlements automatically.

**Acceptance Scenarios**:

1. **Given** a pending upgrade request (e.g., adding a seat), **When** the user confirms they want to pay, **Then** the system calculates the prorated total and provides a Stripe payment link.
2. **Given** a successful payment event from Stripe, **When** the webhook is received, **Then** the system automatically updates the business record to include the new seat/addon and notifies the user (if possible) or reflects it in the next status check.

---

### User Story 3 - Expand Seats (Priority: P2)

As a growing business, I want to add more seats to my subscription through the chat, so that I can onboard new employees (like salespeople) without administrative friction.

**Why this priority**: Key scaling metric and revenue driver.

**Independent Test**: Can be tested by requesting "add 2 seats", verifying the payment flow, and checking if the allowed user limit for the business increases.

**Acceptance Scenarios**:

1. **Given** I am in BILLING state, **When** I say "add 2 seats", **Then** the system quotes the price for the additional seats and asks for confirmation to generate a payment link.
2. **Given** I have purchased extra seats, **When** I try to add a new user to my business, **Then** the system allows it up to the new limit (validating the purchase worked).

---

### User Story 4 - Purchase Feature Addons (Priority: P2)

As a business owner, I want to add capabilities like "Employee Management" or "Campaign Messaging" to my account, so that I can access advanced tools.

**Why this priority**: Unlocks advanced functionality partitioned by the new "scope" system.

**Independent Test**: Can be tested by requesting various addons defined in the YAML config and verifying they render correctly in the billing summary and unlock associated permissions.

**Acceptance Scenarios**:

1. **Given** I am in BILLING state, **When** I say "list addons", **Then** the system shows available addons from the configuration (e.g., Employee Management, Campaign Messaging) with prices.
2. **Given** I request "add Campaign Messaging", **When** I complete payment, **Then** the addon is marked as 'Active' on my account.

---

### User Story 5 - Tool Scope Enforcement (Priority: P1)

As the system administrator, I want specific tools to be restricted to businesses with the corresponding addon, so that premium features are properly gated.

**Why this priority**: Ensures monetization logic works. If tools work without paying, the billing system is moot.

**Independent Test**: Can be tested by trying to invoke a "scoped" tool (e.g., a campaign tool) with and without the required addon in the business's profile.

**Acceptance Scenarios**:

1. **Given** a business WITHOUT the "Campaign Messaging" addon, **When** a user tries to use a campaign-related tool, **Then** the tool execution is blocked, and the system informs the user they need the "Campaign Messaging" addon.
2. **Given** a business WITH the addon, **When** the user invokes the tool, **Then** it executes successfully.
3. **Given** a "Standard" tool (no scope), **When** any user invokes it, **Then** it works regardless of addons.

---

### User Story 6 - Usage Tracking & Overage Billing (Priority: P1)

As a business owner, I want to know how many messages I've sent and be billed automatically for overages, so that I don't get service interruptions while paying for what I use.

**Why this priority**: Essential for cost recovery (SMS/WhatsApp costs).

**Independent Test**: Can be tested by simulating sending 1001 messages and verifying the billing status shows overage and the estimated cost increases.

**Acceptance Scenarios**:

1. **Given** a business has sent 500 messages this month (under 1000 limit), **When** they check billing status, **Then** it shows "Messages: 500/1000 (Included)".
2. **Given** a business has sent 1050 messages, **When** they check billing status, **Then** it shows "Messages: 1050 (50 overage). Estimated Overage Cost: $1.00".
3. **Given** the billing cycle ends, **When** the invoice is generated, **Then** it includes the $1.00 overage charge.

---

### Edge Cases

- **Payment Failure**: What happens if the user clicks the link but the payment fails or is cancelled? (System should assume no change until successful webhook).
- **Concurrent Updates**: What occurs if two admins specified for the same business try to update billing simultaneously? (Database transactions should handle this, last write or additive logic).
- **Pro-ration Complexity**: How are mid-cycle additions calculated? (MVP: Simply charge a calculated "pending" amount passed from the app logic, or rely on Stripe's proration if using Subscriptions API. For MVP, we will assume the app calculates a specific "pay now" amount for the remainder or a fixed setup fee, as specified "app calculates total").
- **Addon Removal**: How do users downgrade? (MVP: Instruct them to contact support, or "remove addon" command that cancels at period end).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a conversational state `BILLING` accessible via "settings" or direct command.
- **FR-002**: System MUST load available addons, prices, and their required scopes from a configuration file (`billing_config.yaml` or similar).
- **FR-003**: System MUST store a business's "subscription status" including: Plan Tier, Seat Count, and List of Active Addons.
- **FR-004**: System MUST implement a `Scope` check mechanism in the Tool Executor or Service layer that validates if the calling business possesses the required scope for a tool before execution.
- **FR-005**: System MUST be able to calculate a total price for a requested upgrade (Seats * Price + Addon Price) and generate a Stripe Payment Link.
- **FR-006**: System MUST expose a generic webhook endpoint (or specific Stripe endpoint) to receive `checkout.session.completed` (or similar) events and update the business's entitlements securely.
- **FR-007**: System MUST allow adding "Seats" independently of "Addons".
- **FR-008**: System MUST provide a clear confirmation message with the total amount before generating the payment link.
- **FR-009**: System MUST track the number of outgoing messages per business per billing cycle.
- **FR-010**: System MUST include the first 1000 messages per month in the base plan at no extra cost.
- **FR-011**: System MUST accumulate usage and charge a set fee (e.g. $0.02) per message for every message exceeding the 1000 message limit, added to the invoice at the end of the billing cycle.
- **FR-012**: System MUST display current message usage and estimated overage costs in the billing status response.

### Key Entities

- **BusinessSubscription**: Extends valid `Business` model or new related entity. Tracks `seat_limit`, `active_addons` (JSON list or relationship), `stripe_customer_id`, `subscription_status`.
- **AddonConfig**: In-memory representation of the YAML config (id, name, description, price, required_scope).
- **ToolDefinition**: Updates existing tool definitions to include an optional `required_scope` field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view their correct quota and addon status within 1 interaction ("billing").
- **SC-002**: Users can generate a valid payment link for an upgrade within 3 conversational turns.
- **SC-003**: 100% of tool invocations requiring a scope are blocked for non-compliant businesses.
- **SC-004**: Valid payment webhooks result in updated business entitlements in the database within 5 seconds of receipt.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/011-employee-management-dashboard/spec.md
---

# Feature Specification: Employee Management Dashboard

**Feature Branch**: `011-employee-management-dashboard`  
**Created**: 2026-01-20  
**Status**: Draft  
**Input**: User description: "Employee management system. We currently have job scheduled for a day, and have employees working between them. Add a screen (see what state machine functionality we have in the system), where an employer can assign jobs to employees, kind of like Jobber and other systems do it. Employees management: John's schedule: 8:00 - job A... Unscheduled jobs: [jobs]. To schedule, say 'Assing #120, 121, 122 to John'..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Employee Schedule Dashboard (Priority: P1)

As a Business Owner, I want to see a consolidated text view of all my employees' schedules and pending jobs so that I can decide who is available for work this week.

**Why this priority**: this is the core "Screen" requested, enabling decision making. Without visibility, assignment is blind.

**Independent Test**: Can be fully tested by seeding jobs and employees in the DB and verifying the "Show schedule" command output correlates with the data.

**Acceptance Scenarios**:

1. **Given** there are employees with assigned jobs and some unassigned pending jobs, **When** I send "Show schedule" (or similar), **Then** I receive a specific formatted message listing each employee, their jobs sorted by time/sequence, and a list of unassigned jobs at the bottom.
2. **Given** I am a standard member (not owner), **When** I try to view schedule, **Then** I am denied access or ignore.

---

### User Story 2 - Assign Jobs to Employees (Priority: P1)

As a Business Owner, I want to assign specific jobs to specific employees using simple natural language commands like "Assign #123 to John" so that I can distribute work efficiently without complex forms.

**Why this priority**: This is the primary action taken on the dashboard.

**Independent Test**: Can be tested by creating an unassigned job #123 and an employee "John", sending the command, and verifying `job.employee_id` is updated.

**Acceptance Scenarios**:

1. **Given** an unassigned job #101 and employee "Alice", **When** I say "Assign #101 to Alice", **Then** the system replies confirming the assignment and the job is updated in the database.
2. **Given** multiple unassigned jobs (#101, #102), **When** I say "Assign #101 and #102 to Bob", **Then** both jobs are assigned to Bob.
3. **Given** an ambiguous name "John" (two Johns exist), **When** I try to assign, **Then** the system asks for clarification (e.g. "Which John? John A or John B?").

---

### User Story 3 - Reassign/Move Jobs (Priority: P2)

As a Business Owner, I want to move a job from one employee to another or unassign it if plans change.

**Why this priority**: Schedules change frequently; rigidity would make the system unusable.

**Independent Test**: Assign a job to User A, then command "Assign #123 to User B", verify ownership change.

**Acceptance Scenarios**:

1. **Given** Job #101 is assigned to Alice, **When** I say "Assign #101 to Bob", **Then** the job is reassigned to Bob and Alice's schedule no longer shows it.
2. **Given** a job, **When** I say "Unassign #101", **Then** it returns to the "Unscheduled" list.

### Edge Cases

- **Ambiguous Names**: Multiple employees with the same first name. System should prompt or verify.
- **Invalid Job IDs**: User types "#9999" which doesn't exist. System should reply nicely ("Job #9999 not found").
- **Non-Employee Users**: User acts on a valid User ID who is not a 'member' or 'employee'. System should probably allow it but warn, or strictly enforce roles.
- **Completed Jobs**: Assigning a job that is already 'completed'. System should probably block or warn.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support an `employee_id` association on the `Job` model, querying `User` entities.
- **FR-002**: The `User` model roles MUST differentiate between Owner (Manager) and Employees (Members) to list them in the dashboard.
- **FR-003**: The system MUST implement a "Dashboard View" generator that queries:
  - All Users with 'member'/'employee' role.
  - All Jobs for "today" (or specified date) assigned to those users.
  - All Jobs with status 'pending' (and unassigned) as "Unscheduled".
- **FR-004**: The output format MUST match the user's requested layout:

    ```
    Employees management:
    [Name]'s schedule:
    [Time/Order] - [Description] #[ID] (Location)
    ...
    Unscheduled jobs:
    [Description] #[ID]
    ```

- **FR-005**: The system MUST parse commands matching patterns like "Assign #[ID] to [Name]" or "Move #[ID] to [Name]".
- **FR-006**: This functionality MUST be restricted to Users with `role='owner'`.

### Key Entities

- **Job**: Modified to include `employee_id` (FK to User) and potentially `scheduled_time` if not present.
- **User**: Used as Employee entity. Filtered by role.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Owners can view the full team schedule in a single message response < 2 seconds.
- **SC-002**: Assignment commands ("Assign #123 to John") are correctly parsed and executed 95% of the time without re-prompting (unless ambiguous).
- **SC-003**: The system successfully handles identical names by prompting for clarification or using unique identifiers.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/012-conversational-quotations/spec.md
---

# Feature Specification: Conversational Quotations

**Feature Branch**: `012-conversational-quotations`
**Created**: 2026-01-20
**Status**: Draft
**Mission**: software-dev
**Input**: User wants a quotation system where "send an invoice to John, clean 15 windows for 150$" creates a quote, looks up John, infers line items, and allows confirmation via text or website. Confirmation creates a Job.

## 1. Overview

The Conversational Quotations system allows business owners to send formal price proposals to customers using natural language. Unlike invoices (which bill for completed work), quotes represent a promise of service and price. Once a customer accepts a quote, the system automatically transitions it into an active, billable Job.

## 2. User Scenarios & Testing

### User Story 1 - Generate Quote from Natural Language (Priority: P1)

As a business owner, I want to say "send a quote to John for 10 windows at $50" and have the system generate a professional proposal automatically.

**Acceptance Scenarios**:

1. **Given** a customer "John" and a "Window Cleaning" service in the catalog ($5 default), **When** the user says "Send quote to John, clean 10 windows for $50", **Then** the system:
    - Identifies John's phone number.
    - Creates a Quote with a "Window Cleaning" line item (Qty 10, Unit Price $5, Total $50).
    - Generates a PDF/Link and sends it via the configured channel (WhatsApp/SMS).
2. **Given** ambiguous Johns, **When** "Send quote to John..." is requested, **Then** the system performs resolution (asking which John).

### User Story 2 - Customer Confirmation via Text (Priority: P1)

As a customer, I want to reply "Confirm" to a quote message to book the job immediately.

**Acceptance Scenarios**:

1. **Given** a Quote has been sent to a customer, **When** the customer replies "Confirm" or "Confirm invoice", **Then** the system:
    - Updates the Quote status to `ACCEPTED`.
    - Automatically creates a `Job` record for the customer with the line items from the quote.
    - Notifies the business owner that a new job has been booked.

### User Story 3 - Confirmation via External Website (Priority: P2)

As a business owner, I want the quote link to lead to a website where the customer can confirm, so the process feels professional.

**Acceptance Scenarios**:

1. **Given** a Quote link is clicked and the customer confirms on the external site, **When** the external site sends a callback/update to the CRM, **Then** the system transitions the Quote to `ACCEPTED` and creates a `Job` just like the text confirmation flow.

### User Story 4 - Promote Request to Quote (Priority: P2)

As a business owner, I want to satisfy a customer request by sending them a formal quote instead of just scheduling a job directly.

**Acceptance Scenarios**:

1. **Given** an existing customer request (e.g., "I need my roof fixed"), **When** the business owner chooses to "Promote to Quote", **Then** the system:
    - Creates a new Quote based on the request content.
    - Links the Quote to the original Request (or resolves the Request).
    - Allows the user to review/send the quote.

---

## 3. Requirements

### Functional Requirements

- **FR-001**: System MUST identify the target customer from natural language (Name/Phone) using existing lookup logic.
- **FR-002**: System MUST infer `LineItem`s from the request using the Service Catalog (Spec 004).
- **FR-003**: System MUST generate a unique `Quote` entity.
- **FR-004**: System MUST generate a professional PDF proposal (similar styling to Spec 006).
- **FR-005**: System MUST provide a public-facing URL for each quote (for the external confirmation website).
- **FR-006**: System MUST support status transitions: `DRAFT` -> `SENT` -> `ACCEPTED` / `REJECTED`.
- **FR-007**: System MUST automatically create a `Job` entity (Spec 001) upon a Quote moving to `ACCEPTED`.

- **FR-008**: System MUST support "Confirm" intent detection on incoming customer messages for active quotes.
- **FR-009**: System MUST support promoting a `Request` entity to a `Quote` (similar to "Request -> Job" promotion), preserving customer context and description.

### Key Entities

- **Quote**:
  - `id`: Unique ID.
  - `customer_id`: Link to Customer.
  - `line_items`: Collection of items (snapshot).
  - `total_amount`: Calculated sum.
  - `status`: [DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED].
  - `external_link`: URL for the proposal website.
  - `job_id`: Reference to the Job created upon acceptance (optional).
- **Job**: (Existing) - will be created from Quote data.

---

## 4. Success Criteria

### Measurable Outcomes

- **SC-001**: Speed: A quote can be generated in under 3 seconds from a single text command.
- **SC-002**: Automation: 100% of "Confirm" replies on valid quotes result in a created Job record without manual intervention.
- **SC-003**: Accuracy: Line item inference matches Spec 004 precision (100% for clear "Qty + Total" inputs).

---

## 4. Tax Calculation

### Overview

Quotes must accurately calculate and display applicable taxes using the Stripe Tax API. The system will query Stripe Tax to determine the correct tax rates based on the business location, customer location, and service type.

### Business Settings

Businesses can configure how taxes are applied to their pricing:

- **Tax Application Mode**: Toggle between "Tax Included" and "Tax Added"
  - **Tax Included**: The price shown to customers already includes tax (tax is calculated backwards from the total)
  - **Tax Added**: Tax is calculated and added on top of the stated price
  - This setting is stored in the `Business` model as `tax_mode` field

### Tax Functional Requirements

- **FR-TAX-001**: System MUST integrate with Stripe Tax API to calculate accurate tax amounts for quotes
- **FR-TAX-002**: System MUST respect the business's `tax_mode` setting when calculating quote totals
- **FR-TAX-003**: System MUST display tax breakdown on quote PDFs (tax rate, tax amount, subtotal, total)
- **FR-TAX-004**: System MUST handle tax calculation errors gracefully (fallback to 0% tax with warning)
- **FR-TAX-005**: System MUST preserve tax calculation when converting accepted Quote to Job
- **FR-TAX-006**: System MUST recalculate taxes if quote line items are modified before sending

### Tax Display

Quotes must clearly show:

- Subtotal (before tax for "Tax Added" mode, or net amount for "Tax Included" mode)
- Tax rate(s) applied
- Tax amount
- Grand total

---

## 5. Assumptions & Risks

- **Assumption**: The external website for quote confirmation will communicate back to this CRM via an API endpoint or webhook to be defined.
- **Risk**: Overlapping quotes (sent multiple quotes to one customer) might make "Confirm" ambiguous if not handled by checking the most recent active quote.
- **Risk**: Text-based confirmation might be triggered by accident if the customer's "Confirm" refers to something else (mitigated by checking context/timeouts).

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/013-autoroute-optimization/spec.md
---

# Feature Specification: Autoroute Optimization

**Feature Branch**: `013-autoroute-optimization`
**Created**: 2026-01-21
**Status**: Draft
**Mission**: software-dev

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Autoroute Optimization (Priority: P1)

As a Business Owner, I want to automatically generate an optimal schedule for all my employees and pending jobs for a specific day so that travel time is minimized and valid availability windows are respected.

**Why this priority**: Core value proposition of the feature.

**Independent Test**:

1. Setup: 2 Employees (A, B) with start locations.
2. Setup: 4 Jobs (J1-J4) with locations and durations.
3. Action: Run `autoroute today`.
4. Result: System proposes a schedule assigning jobs to A and B with logical geographical grouping.

**Acceptance Scenarios**:

1. **Given** a set of unassigned jobs and available employees, **When** I run `autoroute [date]`, **Then** the system returns a summary of the proposed schedule (Routes, Total Distance, Jobs Assigned).
2. **Given** a customer with availability 10:00-12:00, **When** autoroute runs, **Then** the job is scheduled within that window or left unassigned if impossible.
3. **Given** no solution is found for some jobs, **When** autoroute runs, **Then** those jobs remain in "Unscheduled" list in the preview.

---

### User Story 2 - Confirm and Apply Schedule (Priority: P1)

As a Business Owner, I want to confirm the proposed route so that the jobs are actually assigned and scheduled in the system.

**Why this priority**: Completes the workflow.

**Independent Test**:

1. Run autoroute (preview).
2. Send "Confirmed".
3. Verify database: Jobs have `scheduled_at` and `employee_id` set.

**Acceptance Scenarios**:

1. **Given** a generated preview, **When** I confirm, **Then** all jobs in the proposal are updated in the database.
2. **Given** a confirmation, **When** finished, **Then** the system asks "Do you want to notify customers?" (handoff to Msg Spec).

---

### User Story 3 - Employee Start Locations (Priority: P2)

As a Business Owner or Employee, I want to define where the employee starts their day so that routing is accurate and efficient.

**Why this priority**: Essential for accurate travel time calculation.

**Acceptance Scenarios**:

1. **Given** an employee User profile, **When** the Owner or the Employee themselves update settings, **Then** they can set a `default_start_location` (lat/lng or address).
2. **Given** an employee receives a notification about their schedule, **When** they realize their start location is wrong, **Then** they can use a command to update it for future routing.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store `availability_windows` on the `Customer` model (list of start/end times per day).
- **FR-002**: The system MUST store `default_start_location` on the `User` model.
- **FR-003**: The system MUST store `estimated_duration` on `Service` (default) and `Job` (override) models.
- **FR-004**: The system MUST implement a `RoutingService` that interfaces with OpenRouteService API (VRP endpoint).
- **FR-005**: The `autoroute [date]` command MUST:
  - Collect all unassigned pending jobs for the target date (or all pending if no date specific, assume target date for execution).
  - Collect all "locked" (already assigned) jobs for that date (as constraints).
  - Collect available employees.
  - Build VRP request payload.
  - Send to ORS.
  - Parse response into a human-readable preview.
- **FR-006**: The system MUST provide a confirmation flow to apply the results to the default DB.
- **FR-007**: The system MUST implement a command for users (Owners and Employees) to update their `default_start_location`.

### Key Entities

- **Customer**: Add `availability_windows` (JSON).
- **User**: Add `default_start_location_lat`, `default_start_location_lng`.
- **Job**: Add `estimated_duration` (int, minutes).
- **Service**: Add `estimated_duration` (int, minutes).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Optimization for <50 jobs returns result in <10 seconds.
- **SC-002**: Generated routes respect customer availability windows 100% of the time (or leave job unassigned).
- **SC-003**: "Confirm" action successfully updates all job records atomically.

## Assumptions

- OpenRouteService API key is available in environment variables.
- We trust ORS travel time estimates.
- "Availability" is stored in a simple JSON structure for now (e.g., `[{"start": "09:00", "end": "12:00", "day": "monday"}]` or specific dates? User said "specific time windows... set by business... tommorrow 10am to 12am"). We will store specific datetime ranges or day-of-week recurrence. *Assumption*: For the MVP, we store specific date-time ranges or simple "daily" windows. Let's start with a flexible JSON definition.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/014-live-location-tracking/spec.md
---

# Feature Specification: Live Location Tracking

**Feature Branch**: `014-live-location-tracking`
**Created**: 2026-01-21
**Status**: Draft
**Mission**: software-dev

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Employee Checks In with Live Location (Priority: P1)

As an Employee, I want to share my live location via WhatsApp at the start of my shift so that the system can automatically track my progress without manual updates.

**Why this priority**: this is the data source that enables the entire feature.

**Independent Test**:

1. **Setup**: An Employee user exists in the system with a valid WhatsApp number.
2. **Action**: Employee sends a "Live Location" attachment/message to the HereCRM bot on WhatsApp.
3. **Result**: System acknowledges the location ("Thanks, tracking started").
4. **Verification**: Database `User` record shows updated `current_location_lat`, `current_location_lng`, and `location_last_updated`.

**Acceptance Scenarios**:

1. **Given** an employee chat, **When** they send a live location message, **Then** the system parses the lat/long and updates the employee's record.
2. **Given** an employee chat, **When** they send a static location pin, **Then** the system also accepts it and updates the record (fallback).

### User Story 1b - Non-WhatsApp Location Update (Priority: P2)

As an Employee without WhatsApp, I want to share my location by sending a Google Maps link via SMS so that the system can track me.

**Why this priority**: Supports mixed device fleets and ensures reliability when WhatsApp is unavailable.

**Independent Test**:

1. **Prerequisite**: Employee uses standard SMS/MMS.
2. **Action**: Employee opens Maps app -> Share Location -> Copy/Send Link to HereCRM number.
3. **Result**: System parses the coordinate from the URL shortlink (e.g. `maps.app.goo.gl` or `maps.google.com`) and updates the record.
4. **Response**: "Location updated successfully."

**Acceptance Scenarios**:

1. **Given** a text message containing a Google Maps URL, **When** received, **Then** the system extracts the lat/long.
2. **Given** a system with stale location, **When** the business triggers "Request Location", **Then** the employee receives an SMS asking "Please reply with your current location link".

---

### User Story 2 - Customer Inquires ETA (Priority: P1)

As a Customer waiting for a service, I want to ask "When will you arrive?" and get an instant, accurate estimate so that I don't have to call the office.

**Why this priority**: This is the primary value proposition for the end-user (customer).

**Independent Test**:

1. **Setup**:
   - Customer C has a scheduled Job J with Employee E at the current time (or soon).
   - Employee E has a recent location stored (e.g., 5km away).
2. **Action**: Customer C sends "Where is the technician?" or "When will you arrive?".
3. **Result**: System replies "We are approximately 10 minutes away." (Rounded up to nearest 5 mins)

**Acceptance Scenarios**:

1. **Given** an active job and an employee with a recent location (< 15 mins old?), **When** customer asks for status, **Then** system calls OpenRouteService to calculate driving duration and responds.
2. **Given** an automated inquiry, **When** the employee location is stale (> 30 mins?) or unknown, **Then** the system replies with a generic fallback or attempts to ping the employee (depending on implementation, for MVP: generic fallback "Technician is en route, please contact us for details").
3. **Given** no active job found for the customer right now, **When** they ask, **Then** system replies "You have no immediate appointments scheduled."

---

### User Story 3 - Business Owner Checks Employee Location (Priority: P2)

As a Business Owner, I want to query where a specific employee is so that I can make dispatch decisions.

**Why this priority**: Operational oversight.

**Independent Test**:

1. **Action**: Owner sends command `locate [Employee Name]`.
2. **Result**: System returns a Google Maps link or address of the employee's last known location and timestamp.

**Acceptance Scenarios**:

1. **Given** an admin user, **When** they query a valid employee, **Then** system returns the location info.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be able to receive and parse `location` type messages from the messaging provider (WhatsApp) OR text messages containing standard map URLs (Google/Apple Maps).
- **FR-002**: `User` model MUST store `current_latitude` (float), `current_longitude` (float), and `location_updated_at` (datetime).
- **FR-003**: System MUST provide a mechanism to find the "active job" for a Customer based on their phone number and current time.
  - *Logic*: Find Job where `customer_phone == sender` AND `scheduled_start <= now <= scheduled_end + buffer`.
- **FR-004**: System MUST integrate with OpenRouteService (ORS) Routing API (or Matrix API) to calculate driving time between `Employee.current_location` and `Job.location`.
- **FR-005**: System MUST respond to semantic queries (LLM intent "check_eta" or similar) with the calculated duration rounded UP to the nearest 5 minutes (e.g. 7 mins -> 10 mins).

### Key Entities

- **User (Employee)**:
  - `current_latitude`
  - `current_longitude`
  - `location_updated_at`
- **Job**: Used to link Customer to Employee.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Location updates are processed and available in DB within 5 seconds of receipt.
- **SC-002**: ETA requests return a response within 5 seconds (including ORS API latency).
- **SC-003**: System accurately identifies the correct assigned employee for a querying customer 100% of the time if a valid job exists.

## Assumptions

- **Messaging Provider Capabilities**: We assume the underlying WhatsApp integration (e.g., Twilio API) forwards "Live Location" updates as regular webhooks, or at least sends the initial location and subsequent static updates.
  - *Note*: If "Live Location" is a streaming connection effectively held by the client, we might only get the *initial* pin unless the API supports live updates. We assume for MVP that the employee might need to re-share or the API provides updates.
  - *Refinement*: If the API only gives us the static location at the moment of sharing, the "Live" aspect relies on the employee sharing it *recently*. We will treat any location received as the "current" location.
- **Job Assignment**: We assume the customer asking has a job *currently* assigned to an employee.
- **ORS Availability**: OpenRouteService is up and we have quota.
- **Identification**: We assume we can identify the "Active Job" for a customer purely by their phone number keying into the `Job` -> `Customer` relationship.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/015-ad-automation-integrations/spec.md
---

# 015 - Ad Automation & Integrations

## 1. Overview

This feature introduces a secure integration layer to HereCRM, enabling automated data ingestion (from ads) and conversion reporting (to ads). It eliminates manual data entry for new leads and closes the loop on ad performance by reporting "Booked" jobs back to ad platforms.

## 2. Goals

1. **Automate Ingestion**: Provide secure API endpoints to programmatically create Leads and Requests from external sources (e.g., Zapier, Landing Pages).
2. **Meta CAPI Integration**: Native backend integration with Facebook/Meta Conversions API to report "Booked" jobs as conversions.
3. **Universal Webhooks**: A generic outbound webhook system to notify external tools (Zapier, etc.) when key business events occur.

## 3. User Stories

- **As a Marketer**, I want leads from Facebook/Google Forms to instantly appear in HereCRM so the sales team can contact them immediately.
- **As a Business Owner**, I want `Job Booked` events to be sent back to Facebook Ads so the algorithm optimizes for paying customers, not just leads.
- **As an Integrator**, I want to subscribe to a `job.booked` webhook so I can trigger custom workflows (e.g., send a welcome packet, update Google Sheets) without modifying HereCRM code.

## 4. Functional Requirements

### 4.1 Authentication Base

- **API Keys**: All external endpoints must be protected by an API Key authentication scheme (e.g., `X-API-Key` header).

- **Key Validation**: Middleware must reject requests with invalid or missing keys.

### 4.2 Inbound API

- **Create Lead**: `POST /api/v1/integrations/leads`
  - **Input**: `name` (required), `phone` (required), `email` (optional), `source` (optional).
  - **Output**: JSON with created Customer ID.
  - **Logic**: Checks if customer exists by phone; if not, creates new.

- **Create Request**: `POST /api/v1/integrations/requests`
  - **Input**: Customer info (same as above), `address`, `service_type`, `notes`.
  - **Output**: JSON with created Request ID.
  - **Logic**: Creates customer (if needed), then creates a Service Request linked to them.

### 4.3 Outbound Event Engine

- **Core Event**: The system must detect when a Job transitions to a `BOOKED` state.

- **Dispatcher**: A background task or service method should handle the dispatching of events to configured handlers (Meta, Webhooks) asynchronously to avoid blocking user interactions.

### 4.4 Meta Conversions API (CAPI) Integration

- **Configuration**: Needs `META_PIXEL_ID` and `META_ACCESS_TOKEN` (sys_params or env vars).

- **Event Map**: Map `Job Booked` -> CAPI `Schedule` event.
- **Data Hashing**: User data (email, phone) MUST be normalized and hashed (SHA-256) per Meta's strict privacy requirements before sending.
- **Payload**: Include `event_time`, `user_data` (hashed), `custom_data` (value, currency).

### 4.5 Generic Webhooks

- **Configuration**: Support a list of destination URLs for the `job.booked` event (stored in DB or simple config).

- **Payload**: Standard JSON payload describing the job (ID, Customer Name, Service Type, Price).
- **Security**: Include a signature header (`X-HereCRM-Signature`) generated via HMAC-SHA256 using a shared secret, allowing receivers to verify authenticity.

### 4.6 Edge Cases

- **Invalid/Expired API Key**: Request is denied with 401 Unauthorized.

- **Duplicate Customer**: If a lead matches an existing phone number, update the existing record or log a note (do not create duplicate).
- **External Service Failure**: If Meta CAPI or a Webhook endpoint is down (500/timeout), the system logs the failure without crashing the main transaction. Retry logic is out of scope for MVP but failure must be visible.
- **Missing Data**: If a booked job lacks a customer email/phone (rare), the Meta event is sent with minimal data (or skipped with a warning log), as PII is required for matching.

## 5. Non-Functional Requirements

- **Performance**: Webhook dispatch must not increase the latency of the "Book Job" user action.

- **Reliability**: Failure to send a webhook should be logged but shouldn't rollback the database transaction.
- **Security**: API Keys must be long-ended random strings. Verification must use constant-time comparison to prevent timing attacks.

## 6. Success Criteria

1. **Seamless Ingestion**: A third-party system can successfully create a new Lead in the CRM using only a standard HTTP client and valid API Key.
2. **Verifiable Reporting**: The system successfully emits a "Schedule" event to the configured Meta endpoint whenever a job enters the 'Booked' state.
3. **Secure Handoff**: A 3rd-party webhook receiver can cryptographically verify that a "Job Booked" notification originated from HereCRM using the provided signature.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/016-Employee Guided Workflow/spec.md
---

# Feature Specification: Employee Guided Workflow

**Feature Branch**: `016-employee-guided-workflow`  
**Created**: 2026-01-21  
**Status**: Draft  
**Input**: User description: "Specification closely related to 011-employee-management-dashboard, except on the employee side. At the beginning of a working day, employees will receive bookings of which jobs they are meant to fulfil for the day, and their route for the day, said as addresses. They will get google maps links to their next location... Shown the name of the customer and their phone number. In addition, a business owner can configure certain reminder for them... As they will start their jobs, they will be prompted 'type XYZ to finish the job'. Basically, a convenience layer for the employees."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Daily Schedule Overlook (Priority: P1)

As a Field Employee, I want to receive a summary of my day's work and planned route when I start my shift so that I can mentally prepare for the day's tasks.

**Why this priority**: it establishes the context for the employee's day and meets the core "morning overlook" requirement.

**Independent Test**: Can be tested by scheduling jobs for an employee and verifying that a summary message is generated with the correct sequence and details.

**Acceptance Scenarios**:

1. **Given** an employee has 3 jobs scheduled for today, **When** the shift starts (or on-demand "Overview"), **Then** the system sends a message listing all 3 jobs in order, including addresses and a calculated route summary.
2. **Given** an employee has no jobs scheduled, **When** the shifts starts, **Then** the system sends a polite message indicating no work is currently assigned.

---

### User Story 2 - Automatic Next Job Guidance (Priority: P1)

As a Field Employee, I want the system to automatically send me the details for my next job as soon as I finish the current one, so that I can transition smoothly without checking a dashboard.

**Why this priority**: This is the core "guided" part of the workflow, reducing friction between jobs.

**Independent Test**: Verify that marking Job #1 as "done" triggers an immediate message containing Job #2's details.

**Acceptance Scenarios**:

1. **Given** I am at Job #101, **When** I send "done #101", **Then** the system replies with: "Job #101 completed. Next stop: [Customer Name] at [Address]. [Map Link]. Customer phone: [Phone]. Reminders: [Service Reminders]."
2. **Given** I just completed my last job of the day, **When** I send "done #[ID]", **Then** the system replies confirming completion and stating that no more jobs are scheduled for the day.

---

### User Story 3 - Service-Specific Reminders & Upsells (Priority: P2)

As a Business Owner, I want to attach specific reminders or "nudges" to different types of services so that my employees are prompted to upsell or follow quality protocols at the right time.

**Why this priority**: Provides business value (upsells/quality) beyond simple coordination.

**Independent Test**: Configure a reminder for "Interior Window Cleaning" and verify it appears in the automated message for projects of that service type.

**Acceptance Scenarios**:

1. **Given** a service "Window Cleaning" has a reminder "Offer interior cleaning for $X", **When** an employee is sent the details for a Window Cleaning job, **Then** the message includes that specific reminder text.
2. **Given** a job has multiple services with different reminders, **When** the job details are sent, **Then** all applicable reminders are listed.

---

### User Story 4 - Quick Job Completion (Priority: P1)

As a Field Employee, I want to complete jobs using a simple text command like "done #123" so that I can record my work quickly and move on.

**Why this priority**: Essential for the proactive workflow to function.

**Independent Test**: Send "done #123" to the system and verify the job status in the database changes to 'completed'.

**Acceptance Scenarios**:

1. **Given** Job #123 is 'assigned' to me, **When** I say "done #123", **Then** the status is updated and I receive a confirmation.
2. **Given** Job #123 is already 'completed', **When** I say "done #123", **Then** the system informs me it's already finished.

---

### Edge Cases

- **Out-of-order Completion**: Employee forgets to finish Job #1 and tries to finish Job #2. System should handle this gracefully (perhaps asking if Job #1 is also done).
- **Missing Geocodes**: If a job address isn't geocoded, the map link should fallback to a standard search link or notify the employee.
- **Multiple Employees**: Ensuring "done #123" only works if the job is actually assigned to the sender.
- **Re-routing**: If the schedule changes mid-day, the "Next Job" logic should reflect the updated sequence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST implement a "Shift Starter" event that triggers a summary message to assigned employees at their configured shift start time.
- **FR-002**: The system MUST generate Google Maps navigation links (URL) for each job using coordinates if available, or the full address string.
- **FR-003**: The system MUST listen for "done #[ID]" messages and update the corresponding Job status to 'completed'.
- **FR-004**: Upon successful job completion via the text command, the system MUST automatically query for the next 'assigned' but 'pending' job for that employee and push its details.
- **FR-005**: The `Service` entity MUST be extended to store optional "Reminder Text" or "Upsell Prompts".
- **FR-006**: Automated job detail messages MUST include: Customer Name, Address (with Map link), Phone Number (as a clickable tel: link), and all applicable Service Reminders.
- **FR-007**: The system MUST verify that the sender has permission to mark a job as 'done' (i.e., they are the assigned employee or an owner).

### Key Entities

- **Job**: Tracks status, assigned employee, and sequence in the daily route.
- **Service**: Stores "Type" and associated "Reminder/Nudge" text.
- **User (Employee)**: Stores shift start time and preferred communication channel (WhatsApp/SMS).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of employees with scheduled jobs receive their morning overview message automatically.
- **SC-002**: Transition time (from "done" to "next job" details) is under 3 seconds in typical network conditions.
- **SC-003**: Owners can configure or update a service reminder via the management interface and have it active for the next "push" message immediately.
- **SC-004**: System correctly handles `done #[ID]` commands with 99% accuracy for valid IDs.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/017-strict-tool-level-rbac/spec.md
---

# Feature Specification: Strict Tool-Level RBAC and Persona Enforcement

**Feature Branch**: `017-strict-tool-level-rbac`  
**Created**: 2026-01-21  
**Status**: Draft  
**Input**: User description: "strict role-based access control: All tools that a LLM can call are now scoped. Scoped by accessibility - a business owner can only access them, or an employee. For example, an employee shouldn't have access to billing, to exporting all customers, to sending invoices, etc. Also, an intelligent assistant must be able to only answer queries as an assistant. Also, I suggest adding a \"Manager\" role, who is able to access all tools except billing."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Restricted Tool Access (Priority: P1)

As an **Employee**, I attempt to use a restricted tool (like creating an invoice or exporting all customers) via the AI assistant, so that the assistant prevents unauthorized administrative actions.

**Why this priority**: Core security requirement to prevent data exfiltration and unauthorized billing by non-admin users.

**Independent Test**: An Employee user sends a message like "Export all customers to CSV" or "Send a $100 invoice to John Doe". The assistant attempts to call the tool and receives a "Permission Denied" result, which it then reports to the user.

**Acceptance Scenarios**:

1. **Given** a user with the `EMPLOYEE` role, **When** they ask to "Send an invoice to Bob", **Then** the assistant tool execution fails with a message: "It seems you are trying to send an invoice. Sorry, you don't have permission for that."
2. **Given** a user with the `EMPLOYEE` role, **When** they ask to "Export all jobs", **Then** the assistant tool execution fails with a message: "It seems you are trying to export jobs. Sorry, you don't have permission for that."

---

### User Story 2 - Manager Access Level (Priority: P1)

As a **Manager**, I want to perform all CRM operations (routing, customer management, job updates) but be restricted from billing operations, so that I can handle operations without having full owner privileges.

**Why this priority**: Enables delegation of operational tasks without exposing sensitive billing/financial controls.

**Independent Test**: A Manager user sends a message to "Optimize today's routes" (Success) and then asks to "Change our subscription plan" or "Process a payment" (Denied).

**Acceptance Scenarios**:

1. **Given** a user with the `MANAGER` role, **When** they ask to "Re-route employee X", **Then** the assistant executes the `AutorouteTool` successfully.
2. **Given** a user with the `MANAGER` role, **When** they ask to "Process a customer payment", **Then** the assistant receives a "Permission Denied" message for the billing tool.

---

### User Story 3 - Persona Enforcement for Non-Owners (Priority: P2)

As an **Associate** (Employee or Manager), I ask the assistant a query that requires reading data I don't have full "status" for, so that the assistant answers but reminds me of my restricted role access.

**Why this priority**: Ensures users are aware of their limited permissions and prevents the assistant from appearing "all-powerful" to unauthorized roles.

**Independent Test**: An Employee asks "What is our total revenue this month?". The assistant retrieves the data but appends the required disclaimer.

**Acceptance Scenarios**:

1. **Given** a user with a role other than `OWNER`, **When** they ask a query about restricted features/data, **Then** the assistant answers the query and appends: "The user does not have role-based access to this feature because he doesn't have a status."

---

### Edge Cases

- **Missing Role**: If a user has no assigned role, the system should default to the most restrictive level (`EMPLOYEE`) or deny all tool access.
- **Friendly Name Translation**: If a tool lacks a defined "friendly name" in the configuration, but is called, the system should gracefully handle the error (perhaps using a fallback or raw name if necessary, though the requirement is for friendly names).
- **Multiple Tool Calls**: If an LLM attempts to call multiple tools in a single turn, some authorized and some not, each should be evaluated independently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Role Hierarchy: The system MUST support at least three roles: `OWNER`, `MANAGER`, and `EMPLOYEE`.
- **FR-002**: RBAC Configuration: Tool permissions MUST be defined in a hardcoded `rbac_tools.yaml` file.
- **FR-003**: Tool Scoping: Every tool executable by the LLM MUST be mapped to one or more authorized roles.
- **FR-004**: Execution Interceptor: The tool execution layer MUST verify the current user's role against the `rbac_tools.yaml` before executing any tool.
- **FR-005**: Explicit Denial Message: When access is denied, the system MUST return a message to the LLM in the format: `"It seems you are trying to [friendly tool name]. Sorry, you don't have permission for that."`
- **FR-006**: Friendly Tool Naming: Each tool in the RBAC configuration MUST have a human-readable "friendly name" (e.g., "export jobs" instead of `ExportJobsTool`).
- **FR-007**: Persona Disclaimer: If the current user's role is not `OWNER`, the assistant MUST append the following string to its response when discussing restricted features: `"The user does not have role-based access to this feature because he doesn't have a status."`

### Key Entities *(include if feature involves data)*

- **User Role**: An attribute of the User entity determining their access level (`OWNER`, `MANAGER`, `EMPLOYEE`).
- **RBAC Configuration**: A YAML structure mapping tool identifiers to authorized roles and friendly descriptions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of LLM tool calls are checked against the RBAC configuration before execution.
- **SC-002**: Zero unauthorized tool executions occur for `EMPLOYEE` and `MANAGER` roles during security testing.
- **SC-003**: All permission denied messages use the specified friendly format and correct tool names.
- **SC-004**: Assistant responses to non-owners regarding restricted data consistently include the mandatory status disclaimer.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/018-Stripe Payment Integration/spec.md
---

# Feature Specification: Stripe Payment Integration

**Feature**: Stripe Payment Integration
**Status**: Draft
**Mission**: software-dev

## 1. Overview

This feature integrates **Stripe Connect** into the Whatsapp AI CRM to enable businesses to collect payments seamlessly. It facilitates a specific workflow where businesses (Tenants) can onboard via Stripe Standard Connect, generate professional invoices with embedded payment links, and track payment status automatically. The system leverages Stripe Hosted Checkout for security and simplicity, avoiding the need for a custom payment frontend.

## 2. Functional Requirements

### 2.1. Merchant Onboarding (Stripe Connect)

- **FR-001**: System MUST provide a mechanism for Business Owners to initiate Stripe onboarding (e.g., via a "setup payments" command or settings link).
- **FR-002**: System MUST generate a Stripe OAuth link (Standard Connect) that redirects the user to Stripe's onboarding flow.
- **FR-003**: System MUST handle the OAuth callback to securely retrieve and store the `stripe_connected_account_id` for the Business.
- **FR-004**: System MUST verify the account status (charges_enabled) before allowing payment link generation.

### 2.2. Business Settings for Compliance

- **FR-005**: System MUST allow Business Owners to configure "Official Business Details" separate from operation defaults:
  - Legal Business Name
  - Legal Address (Street, City, Zip, Country)
  - Tax/VAT ID
- **FR-006**: These details MUST be used on generated invoices for compliance.

### 2.3. Payment Link Generation

- **FR-007**: When an Invoice is generated (see `006-professional-invoices`), the system MUST create a corresponding Stripe Checkout Session.
  - **Mode**: Payment (one-time).
  - **Line Items**: Mapped from the Job details.
  - **Destination**: The connected Business account (Direct Charge).
- **FR-008**: The creation request MUST NOT include platform fees (application_fee_amount = 0).

### 2.4. Invoice & Message Enhancement

- **FR-009**: The generated PDF Invoice MUST include a clickable "Pay Now" link pointing to the Stripe Hosted Checkout page.
- **FR-010**: The WhatsApp message delivering the invoice MUST include the direct payment link in the text body (e.g., "Pay securely here: <https://stripe.com/>...").

### 2.5. Payment Status Tracking

- **FR-011**: System MUST expose a webhook endpoint to receive Stripe events (`connect` webhooks).
- **FR-012**: System MUST listen for `checkout.session.completed` events.
- **FR-013**: Upon successful payment, the system MUST:
  - Update the `Invoice` status to `PAID`.
  - Update the associated `Job` status to `PAID` (or equivalent).
  - Send a notification to the Business Owner: "Payment received for Job [ID] / Customer [Name]: [Amount]".

## 3. Data Model Enhancements

- **Business Entity**:
  - `stripe_account_id` (String, nullable): The connected Stripe Account ID (acct_...).
  - `legal_name` (String, nullable)
  - `legal_address` (JSON/String, nullable)
  - `tax_id` (String, nullable)

- **Invoice Entity**:
  - `stripe_session_id` (String, nullable): ID of the checkout session.
  - `payment_link` (String, nullable): The URL to the hosted checkout.
  - `status`: Update enum to include `PENDING_PAYMENT`, `PAID`, `VOID`.
  - `payment_date` (DateTime, nullable).

## 4. User Scenarios

### Scenario 1: Onboarding

1. **Owner** sends: "Setup payments"
2. **System** replies: "Click here to connect your Stripe account and start accepting payments: [Link]"
3. **Owner** clicks link, completes Stripe form, and is redirected back.
4. **System** sends: "✅ Payments enabled! Your account is connected."

### Scenario 2: Sending a Payable Invoice

1. **Owner** sends: "Send invoice to Sarah for Window Cleaning"
2. **System** identifies the job, generates Stripe Checkout link, creates PDF with link.
3. **System** replies: "Invoice sent to you. Forward this to Sarah:\n\n'Here is your invoice for Window Cleaning. You can pay securely online: [Stripe Link]'" and attaches the PDF.
4. **Sarah** clicks the link and pays.
5. **System** (via Webhook) detects payment.
6. **System** notifies Owner: "💰 Payment received! Sarah paid $50.00 for request #123."

### Scenario 3: Checking Payment Status

1. **Owner** sends: "Who hasn't paid?"
2. **System** lists all Invoices with status `SENT` or `PENDING_PAYMENT`.

## 5. Success Criteria

- **SC-001**: Business can successfully link a Stripe account and receive a confirmation message.
- **SC-002**: Generated payment links successfully open a Stripe Checkout page with the correct amount and line items.
- **SC-003**: Payments made on Stripe automatically update the local database status to `PAID` within 1 minute (webhook latency).
- **SC-004**: PDF Invoices contain a valid, reachable URL for payment.

## 6. Assumptions & Risks

- **Stripe Availability**: Assumes businesses are in Stripe-supported regions.
- **Webhook Reliability**: Critical dependency on Stripe webhooks for status updates. Need to handle potential delivery failures (idempotency).
- **Compliance**: The platform (HereCRM) acts as a technology provider, not the merchant of record. The connected business is liable for refunds/disputes.

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/019-business-workflow-defaults/spec.md
---

# Feature Specification: Business Workflow Defaults

**Feature**: Business Workflow Defaults
**Status**: Draft
**Mission**: software-dev

## 1. Overview

Different businesses operate with fundamentally different workflows. A window cleaning service in Ireland may never send formal invoices, while a US-based contractor sends invoices for every job. Some businesses quote on-the-spot, others send formal quotes. Some expect payment immediately, others invoice with net-30 terms.

This feature introduces configurable workflow defaults that allow each business to tailor the system to match their operational reality. These settings control UI visibility, default behaviors, and available functionality—ensuring the system adapts to the business, not the other way around.

## 2. Functional Requirements

### 2.1. Workflow Settings Configuration

Business owners must be able to configure the following workflow preferences:

#### 2.1.1. Invoicing Workflow

Controls how the business handles customer invoicing.

**Options**:

- **Never**: Business never sends invoices
  - Hide all invoice-related UI elements (tabs, buttons, menu items)
  - Disable invoice-related tool calls (e.g., `SendInvoiceTool`)
  - Invoice functionality is completely unavailable
  
- **Manual**: Business sends invoices when needed
  - Show invoice UI in menus and customer/job views
  - User must explicitly initiate invoice creation/sending
  - No automatic prompts or suggestions
  
- **Automatic**: Business regularly sends invoices
  - Show invoice UI
  - System prompts user to send invoices for completed jobs
  - Suggest invoice creation at appropriate workflow stages

**Default**: Manual

#### 2.1.2. Quoting Workflow

Controls how the business handles customer quotes.

**Options**:

- **Never**: Business quotes on-the-spot, no formal quotes
  - Hide all quote-related UI elements
  - Disable quote-related tool calls (e.g., `SendQuoteTool`)
  - Quote functionality is completely unavailable
  
- **Manual**: Business sends quotes when needed
  - Show quote UI in menus and customer views
  - User must explicitly initiate quote creation/sending
  - No automatic prompts
  
- **Automatic**: Business regularly sends quotes
  - Show quote UI
  - System prompts user to send quotes for new leads or requests
  - Suggest quote creation for appropriate customer interactions

**Default**: Manual

#### 2.1.3. Payment Timing

Controls default payment behavior and UI visibility for payment tracking.

**Options**:

- **Always paid on spot**: All jobs are paid immediately upon completion
  - Automatically set `Job.paid = true` for all new jobs
  - Hide payment tracking UI (payment status fields, "mark as paid" buttons)
  - Payment recording functionality is unavailable
  
- **Usually paid on spot**: Most jobs are paid immediately, but exceptions exist
  - Show payment tracking UI
  - Allow manual payment status updates
  - Default `Job.paid = false` (user can mark as paid)
  
- **Paid later**: Jobs are typically invoiced with payment terms
  - Show payment tracking UI
  - Default `Job.paid = false`
  - Payment status must be manually updated

**Default**: Usually paid on spot

#### 2.1.4. Tax Inclusion

Controls whether recorded prices include tax or if tax is added as a surcharge.

**Options**:

- **Prices include tax** (toggle: true/false)
  - `true`: Recorded job prices already include tax (tax-inclusive pricing)
  - `false`: Tax should be calculated and added as a surcharge on invoices

**Default**: true (prices include tax)

**Note**: Tax calculation logic is not implemented yet. This setting prepares the data model for future tax handling.

#### 2.1.5. Payment Terms on Invoices

Controls whether invoices include payment timing information (due dates, net terms).

**Options**:

- **Include payment terms** (toggle: true/false)
  - `true`: Invoices show due dates and payment terms (e.g., "Net 30")
  - `false`: Invoices do not include payment timing information

**Default**: false

#### 2.1.6. Automatic Reminders & Follow-ups

Controls whether the system sends automatic reminders for scheduled jobs and follow-ups.

**Options**:

- **Enable automatic reminders** (toggle: true/false)
  - `true`: System sends automatic reminders for upcoming appointments and follow-ups
  - `false`: No automatic reminders are sent

**Default**: false

### 2.2. Settings Storage

All workflow settings must be stored as **columns** on the `Business` model.

**Fields**:

- `workflow_invoicing` (`never` | `manual` | `automatic`)
- `workflow_quoting` (`never` | `manual` | `automatic`)
- `workflow_payment_timing` (`always_paid_on_spot` | `usually_paid_on_spot` | `paid_later`)
- `workflow_tax_inclusive` (boolean)
- `workflow_include_payment_terms` (boolean)
- `workflow_enable_reminders` (boolean)

### 2.3. Settings Management Interface

Business owners must be able to view and update workflow settings through a conversational interface.

**User Actions**:

- **View current settings**: "show workflow settings" or "show my settings"
  - System displays current workflow configuration in a readable format
  
- **Update settings**: "change workflow settings" or "update settings"
  - System presents each setting with current value and available options
  - User selects new values
  - System confirms changes and updates `Business.settings`

**Permissions**:

- Only users with `role = OWNER` can modify workflow settings
- All users can view their business's workflow settings

### 2.4. Application Behavior Based on Settings

The system must enforce workflow settings across all relevant components:

#### 2.4.1. UI Visibility

- **Invoicing = Never**: Hide invoice tabs, buttons, and menu items
- **Quoting = Never**: Hide quote tabs, buttons, and menu items
- **Payment Timing = Always paid on spot**: Hide payment status fields and "mark as paid" buttons

#### 2.4.2. Tool Availability

- **Invoicing = Never**: Disable `SendInvoiceTool` and related invoice tools
- **Quoting = Never**: Disable `SendQuoteTool` and related quote tools
- **Payment Timing = Always paid on spot**: Disable payment recording tools

#### 2.4.3. Default Values

- **Payment Timing = Always paid on spot**: Set `Job.paid = true` for all new jobs
- **Payment Timing = Usually paid on spot | Paid later**: Set `Job.paid = false` for new jobs

#### 2.4.4. System Prompts

- **Invoicing = Automatic**: Prompt user to send invoices for completed jobs
- **Quoting = Automatic**: Prompt user to send quotes for new leads/requests
- **Enable Reminders = true**: Send automatic reminders for scheduled appointments

### 2.5. Migration and Defaults

For existing businesses without workflow settings:

- Apply default values on first access to settings
- Do not modify existing job payment statuses
- Settings apply to new records created after configuration

## 3. Data Model Changes

### 3.1. Business Entity

 The `Business` entity will be updated with the following columns:

- `workflow_invoicing`
- `workflow_quoting`
- `workflow_payment_timing`
- `workflow_tax_inclusive`
- `workflow_include_payment_terms`
- `workflow_enable_reminders`

**Note**: Database migration is required to add these columns.

## 4. User Scenarios

### Scenario 1: Irish Window Cleaner (Never Invoices, Always Paid On Spot)

1. **Owner** sends: "change workflow settings"
2. **System** presents workflow options
3. **Owner** configures:
   - Invoicing: Never
   - Quoting: Never
   - Payment Timing: Always paid on spot
4. **System** confirms: "✔ Workflow settings updated. Invoices and quotes are now hidden. All jobs will be marked as paid automatically."
5. **Owner** adds a job: "Add: John, window cleaning, €50"
6. **System** creates job with `paid = true` automatically
7. **Owner** views job list: No invoice or payment status columns visible

### Scenario 2: US Contractor (Regular Invoicing, Net-30 Terms)

1. **Owner** sends: "update settings"
2. **Owner** configures:
   - Invoicing: Automatic
   - Quoting: Manual
   - Payment Timing: Paid later
   - Include Payment Terms: true
3. **Owner** completes a job
4. **System** prompts: "Job completed for Sarah Smith ($150). Would you like to send an invoice?"
5. **Owner** confirms
6. **System** generates invoice with payment terms and due date

### Scenario 3: Freelance Consultant (Quotes First, Then Invoices)

1. **Owner** configures:
   - Invoicing: Manual
   - Quoting: Automatic
   - Payment Timing: Paid later
2. **Owner** adds lead: "add lead: TechCorp, 555-0100"
3. **System** prompts: "New lead added. Would you like to send a quote?"
4. **Owner** sends quote
5. Lead accepts, job is created
6. **Owner** manually sends invoice after job completion

### Scenario 4: Viewing Current Settings

1. **User** (Employee) sends: "show workflow settings"
2. **System** replies:

   ```
   📋 Workflow Settings:
   • Invoicing: Manual
   • Quoting: Never
   • Payment: Usually paid on spot
   • Tax: Prices include tax
   • Payment terms on invoices: No
   • Automatic reminders: Enabled
   ```

## 5. Success Criteria

- Business owners can configure all six workflow settings through a conversational interface
- Settings are persisted in `Business.settings` JSON field
- UI elements (tabs, buttons, menus) are hidden when corresponding workflow is set to "Never"
- Tool calls for disabled workflows return appropriate error messages
- Jobs created with "Always paid on spot" setting have `paid = true` by default
- System prompts appear for "Automatic" workflows at appropriate stages
- Settings can be viewed by all users but modified only by owners
- Existing businesses receive sensible defaults without breaking existing data

## 6. Assumptions & Risks

- **UI Framework**: Assumes UI components can conditionally render based on business settings
- **Tool Execution**: Assumes tool executor can check business settings before executing tools
- **Tax Calculation**: Tax calculation logic is not implemented; this feature only adds the toggle for future use
- **Reminder System**: Assumes reminder/scheduling infrastructure exists or will be implemented separately
- **Settings Validation**: Invalid settings values should be rejected with clear error messages
- **Performance**: Reading settings from JSON field on every request should not impact performance significantly (settings can be cached per business)

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/020-quickbooks-accounting-integration/spec.md
---

# Feature Specification: QuickBooks Accounting Integration

**Feature**: QuickBooks Accounting Integration
**Status**: Draft
**Mission**: software-dev

## 1. Overview

This feature integrates QuickBooks Online with HereCRM to automatically synchronize accounting data, enabling businesses to maintain accurate financial records for tax reporting and bookkeeping. The integration provides automated hourly batch synchronization of invoices, payments, customers, and services from HereCRM to QuickBooks, eliminating manual data entry and reducing accounting errors.

Businesses authenticate once via OAuth 2.0, and the system handles all subsequent synchronization automatically with robust error handling and retry logic.

## 2. Functional Requirements

### 2.1. QuickBooks Authentication & Connection

- **FR-001**: System MUST provide a mechanism for Business Owners to initiate QuickBooks connection (e.g., "Connect QuickBooks" button in settings or conversational command).
- **FR-002**: System MUST implement OAuth 2.0 authorization flow using QuickBooks Online API to obtain access tokens.
- **FR-003**: System MUST securely store QuickBooks OAuth tokens (access token, refresh token, realm ID) for each business.
- **FR-004**: System MUST automatically refresh expired access tokens using the refresh token before sync operations.
- **FR-005**: System MUST allow Business Owners to disconnect their QuickBooks account, which removes stored credentials and stops synchronization.
- **FR-006**: System MUST display connection status (Connected/Disconnected) to Business Owners.

### 2.2. Automated Data Synchronization

- **FR-007**: System MUST perform automated batch synchronization every hour for all connected businesses.
- **FR-008**: System MUST synchronize the following data types from HereCRM to QuickBooks:
  - Invoices (new and updated)
  - Payments received
  - Customer/Client information (unidirectional: HereCRM → QuickBooks)
  - Services/Products from the service catalog
- **FR-009**: System MUST track synchronization state for each record to identify new, modified, and already-synced items.
- **FR-010**: System MUST maintain a mapping between HereCRM records and their corresponding QuickBooks IDs (e.g., HereCRM Invoice ID → QuickBooks Invoice ID).

### 2.3. Invoice Synchronization

- **FR-011**: When an invoice is created or updated in HereCRM, it MUST be queued for synchronization in the next hourly batch.
- **FR-012**: System MUST map HereCRM invoice data to QuickBooks Invoice format including:
  - Customer reference
  - Line items (services/products with quantities and prices)
  - Invoice date
  - Due date
  - Total amount
  - Invoice status
- **FR-013**: If an invoice already exists in QuickBooks (duplicate detected via mapping), system MUST update the existing QuickBooks invoice rather than creating a new one.

### 2.4. Payment Synchronization

- **FR-014**: When a payment is recorded in HereCRM, it MUST be queued for synchronization in the next hourly batch.
- **FR-015**: System MUST create Payment records in QuickBooks linked to the corresponding Invoice.
- **FR-016**: System MUST include payment details: amount, payment date, payment method, and reference to the invoice.

### 2.5. Customer Synchronization

- **FR-017**: System MUST synchronize customer/client records from HereCRM to QuickBooks (unidirectional).
- **FR-018**: System MUST map customer data including: name, phone number, email, address (if available).
- **FR-019**: If a customer already exists in QuickBooks, system MUST update the existing record.
- **FR-020**: System MUST create customers in QuickBooks before syncing invoices that reference them.

### 2.6. Service/Product Synchronization

- **FR-021**: System MUST synchronize services from HereCRM service catalog to QuickBooks as Items/Products.
- **FR-022**: System MUST map service data including: name, description, default price.
- **FR-023**: If a service already exists in QuickBooks, system MUST update the existing item.
- **FR-024**: System MUST create services in QuickBooks before syncing invoices that reference them.

### 2.7. Error Handling & Retry Logic

- **FR-025**: If QuickBooks API is unavailable or returns an error, system MUST retry the failed operation up to 3 times with exponential backoff (e.g., 1 minute, 2 minutes, 4 minutes).
- **FR-026**: If all retry attempts fail, system MUST notify the Business Owner with details of the failure.
- **FR-027**: If a record cannot be synced due to missing required data (e.g., customer missing address required by QuickBooks), system MUST:
  - Skip that specific record
  - Log the validation error
  - Notify the Business Owner with details of which record failed and why
  - Continue processing other records in the batch
- **FR-028**: System MUST track failed synchronization attempts and allow manual retry or correction.

### 2.8. Sync Status & Visibility

- **FR-029**: System MUST provide Business Owners visibility into synchronization status:
  - Last successful sync timestamp
  - Number of records synced in last batch
  - Any pending errors or failures
- **FR-030**: System MUST allow Business Owners to manually trigger an immediate sync outside the hourly schedule.
- **FR-031**: System MUST maintain a sync log/history showing recent synchronization activities and outcomes.

## 3. Data Model Enhancements

### Business Entity

- `quickbooks_realm_id` (String, nullable): QuickBooks company/realm identifier
- `quickbooks_access_token` (String, encrypted, nullable): OAuth access token
- `quickbooks_refresh_token` (String, encrypted, nullable): OAuth refresh token
- `quickbooks_token_expiry` (DateTime, nullable): Access token expiration timestamp
- `quickbooks_connected_at` (DateTime, nullable): When QuickBooks was first connected
- `quickbooks_last_sync` (DateTime, nullable): Timestamp of last successful sync

### Invoice Entity

- `quickbooks_id` (String, nullable): QuickBooks Invoice ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### Payment Entity

- `quickbooks_id` (String, nullable): QuickBooks Payment ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### Customer Entity

- `quickbooks_id` (String, nullable): QuickBooks Customer ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### Service Entity

- `quickbooks_id` (String, nullable): QuickBooks Item/Product ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### SyncLog Entity (New)

- `id` (Integer, primary key)
- `business_id` (Integer, foreign key)
- `sync_timestamp` (DateTime): When sync occurred
- `sync_type` (Enum): SCHEDULED, MANUAL
- `records_processed` (Integer): Total records in batch
- `records_succeeded` (Integer): Successfully synced
- `records_failed` (Integer): Failed to sync
- `error_details` (JSON, nullable): Details of any errors
- `status` (Enum): SUCCESS, PARTIAL_SUCCESS, FAILED

## 4. User Scenarios & Testing

### Scenario 1: Initial QuickBooks Connection

1. **Business Owner** navigates to settings or sends: "Connect QuickBooks"
2. **System** replies: "Click here to connect your QuickBooks account: [OAuth Link]"
3. **Business Owner** clicks link, authorizes HereCRM in QuickBooks portal
4. **System** receives OAuth callback, stores credentials
5. **System** confirms: "✅ QuickBooks connected! Your data will sync automatically every hour."

**Acceptance Criteria**:

- OAuth flow completes successfully
- Credentials are securely stored
- Connection status shows "Connected"

### Scenario 2: Automatic Hourly Sync (Happy Path)

1. **System** triggers hourly sync job at scheduled time
2. **System** identifies 5 new invoices, 3 payments, 2 new customers, 1 new service
3. **System** syncs customers first (dependency)
4. **System** syncs services second (dependency)
5. **System** syncs invoices third
6. **System** syncs payments last
7. **System** updates sync log: "11 records synced successfully"
8. **System** updates `last_sync` timestamp

**Acceptance Criteria**:

- All records sync in correct dependency order
- QuickBooks IDs are stored in HereCRM
- Sync status updated to SYNCED
- No errors logged

### Scenario 3: Sync with Missing Customer Data

1. **System** triggers hourly sync
2. **System** attempts to sync Invoice #123 for Customer "John Doe"
3. **QuickBooks API** rejects customer creation (missing required address field)
4. **System** skips Invoice #123, logs error
5. **System** continues syncing other records successfully
6. **System** notifies Business Owner: "⚠️ Sync completed with errors. Invoice #123 for John Doe could not be synced: Customer address is required by QuickBooks. Please update customer details."

**Acceptance Criteria**:

- Failed record is skipped, not retried in same batch
- Other records sync successfully
- Business Owner receives specific error notification
- Error details logged for review

### Scenario 4: QuickBooks API Temporarily Unavailable

1. **System** triggers hourly sync
2. **System** attempts to connect to QuickBooks API
3. **QuickBooks API** returns 503 Service Unavailable
4. **System** waits 1 minute, retries (Attempt 2)
5. **QuickBooks API** still unavailable
6. **System** waits 2 minutes, retries (Attempt 3)
7. **QuickBooks API** still unavailable
8. **System** waits 4 minutes, retries (Attempt 4 - final)
9. **QuickBooks API** responds successfully
10. **System** completes sync normally

**Acceptance Criteria**:

- Retry logic executes with exponential backoff
- Sync eventually succeeds
- No duplicate records created

### Scenario 5: Manual Sync Trigger

1. **Business Owner** sends: "Sync QuickBooks now"
2. **System** initiates immediate sync outside scheduled time
3. **System** processes all pending records
4. **System** replies: "✅ QuickBooks sync completed. 7 records synced successfully."

**Acceptance Criteria**:

- Manual sync executes immediately
- Does not interfere with scheduled sync
- Results reported to owner

### Scenario 6: Viewing Sync Status

1. **Business Owner** sends: "QuickBooks status"
2. **System** replies:

   ```
   📊 QuickBooks Sync Status
   
   Connection: ✅ Connected
   Last Sync: 15 minutes ago
   Last Batch: 12 records synced
   Pending Errors: 1
   
   ⚠️ 1 invoice failed to sync (missing customer data)
   ```

**Acceptance Criteria**:

- Status shows accurate connection state
- Displays last sync time
- Shows any pending errors with details

### Scenario 7: Disconnecting QuickBooks

1. **Business Owner** sends: "Disconnect QuickBooks"
2. **System** confirms: "Are you sure? This will stop automatic syncing."
3. **Business Owner** confirms: "Yes"
4. **System** removes OAuth credentials
5. **System** replies: "QuickBooks disconnected. You can reconnect anytime."

**Acceptance Criteria**:

- Credentials securely deleted
- Sync jobs no longer run for this business
- Connection status shows "Disconnected"

## 5. Success Criteria

- **SC-001**: Business Owners can successfully connect their QuickBooks account via OAuth 2.0 in under 2 minutes.
- **SC-002**: Automated hourly sync completes for 95% of businesses without errors.
- **SC-003**: When sync errors occur, Business Owners receive actionable error notifications within 5 minutes.
- **SC-004**: Invoices created in HereCRM appear in QuickBooks within 65 minutes (worst case: just after hourly sync).
- **SC-005**: Duplicate records are prevented - existing QuickBooks records are updated rather than creating duplicates.
- **SC-006**: Failed syncs retry automatically up to 3 times before notifying the owner.
- **SC-007**: Business Owners can view sync status and history at any time.
- **SC-008**: Manual sync triggers complete within 2 minutes for typical business data volumes (up to 100 records).

## 6. Assumptions & Constraints

### Assumptions

- Businesses using this feature have active QuickBooks Online subscriptions (not QuickBooks Desktop).
- Businesses operate in regions where QuickBooks Online is available.
- HereCRM has a registered QuickBooks app with valid OAuth credentials (client ID, client secret).
- QuickBooks API rate limits are sufficient for hourly batch processing (typical limits: 500 requests per minute).
- Business Owners have administrative access to their QuickBooks account to authorize the integration.
- Internet connectivity is generally reliable for both HereCRM and QuickBooks services.

### Constraints

- **Sync Frequency**: Hourly batch sync (not real-time) to balance data freshness with API rate limits and system load.
- **Unidirectional Sync**: Data flows only from HereCRM to QuickBooks (no data pulled from QuickBooks except for tax calculation in future features).
- **OAuth Token Lifespan**: QuickBooks access tokens expire after 1 hour; refresh tokens expire after 100 days of inactivity.
- **Data Mapping Limitations**: Some HereCRM fields may not have direct QuickBooks equivalents and may require transformation or omission.
- **API Dependencies**: Feature functionality is dependent on QuickBooks API availability and stability.

### Out of Scope

- **Tax Calculation**: Automatic tax calculation using QuickBooks or Stripe Tax is explicitly excluded from this feature (deferred to future enhancement).
- **QuickBooks → HereCRM Sync**: Pulling data from QuickBooks into HereCRM is not included.
- **QuickBooks Desktop**: Only QuickBooks Online is supported.
- **Financial Reporting**: Generating reports or analytics from QuickBooks data is not included.
- **Multi-Currency**: Initial version assumes single currency per business.
- **Custom Field Mapping**: Business-specific custom field mapping is not supported in initial version.

## 7. Dependencies

- **Existing Features**:
  - `006-professional-invoices`: Invoice generation and management
  - `004-line-items-and-service-catalog`: Service catalog for product/item sync
  - Customer/Client management system
  - Payment recording system

- **External Services**:
  - QuickBooks Online API (v3)
  - QuickBooks OAuth 2.0 authorization server

- **Infrastructure**:
  - Scheduled job system (cron or task scheduler) for hourly sync
  - Secure credential storage (encryption at rest)
  - Webhook/callback endpoint for OAuth flow

## 8. Security & Compliance

- **SEC-001**: OAuth tokens MUST be encrypted at rest in the database.
- **SEC-002**: OAuth tokens MUST be transmitted only over HTTPS.
- **SEC-003**: Refresh tokens MUST be rotated according to QuickBooks best practices.
- **SEC-004**: System MUST implement proper OAuth state parameter validation to prevent CSRF attacks.
- **SEC-005**: Access to QuickBooks credentials MUST be restricted to authorized system components only.
- **SEC-006**: Sync logs MUST NOT contain sensitive financial data in plain text.
- **SEC-007**: Business Owners MUST be able to revoke QuickBooks access at any time.

## 9. Edge Cases & Error Scenarios

### Edge Case 1: Token Refresh Failure

- **Scenario**: Refresh token has expired or been revoked
- **Handling**: Notify Business Owner that QuickBooks connection has been lost and requires re-authorization

### Edge Case 2: Duplicate Detection Failure

- **Scenario**: Mapping record exists but QuickBooks record was manually deleted
- **Handling**: Attempt to update fails, system creates new record and updates mapping

### Edge Case 3: Concurrent Modifications

- **Scenario**: Invoice updated in HereCRM during sync operation
- **Handling**: Next sync cycle will capture the latest changes (eventual consistency)

### Edge Case 4: Large Batch Size

- **Scenario**: Business has 500+ pending records to sync
- **Handling**: Process in smaller batches to respect API rate limits, may take multiple sync cycles

### Edge Case 5: Partial Batch Failure

- **Scenario**: 10 out of 50 records fail due to validation errors
- **Handling**: Successfully sync 40 records, log 10 failures, notify owner with summary

### Edge Case 6: QuickBooks Account Suspension

- **Scenario**: Business's QuickBooks subscription expires or is suspended
- **Handling**: API returns authorization error, system notifies owner that QuickBooks access is unavailable

## 10. Future Enhancements

The following enhancements are explicitly out of scope for this feature but may be considered in future iterations:

- **Tax Calculation Integration**: Leverage QuickBooks or Stripe Tax for automatic tax calculation on invoices
- **Bidirectional Sync**: Pull data from QuickBooks into HereCRM (expenses, bills, vendor payments)
- **Real-time Sync**: Webhook-based real-time synchronization instead of hourly batches
- **Custom Field Mapping**: Allow businesses to map custom fields between systems
- **Multi-Currency Support**: Handle businesses operating in multiple currencies
- **Advanced Reporting**: Financial reports and dashboards using QuickBooks data
- **QuickBooks Desktop Support**: Extend integration to QuickBooks Desktop via Web Connector
- **Selective Sync**: Allow businesses to choose which data types to sync
- **Conflict Resolution**: Handle scenarios where records are modified in both systems

---

FILE: /home/maksym/Work/proj/HereCRM/kitty-specs/021-expenses-payroll-ledger/spec.md
---

# Feature Specification: Expenses & Payroll Ledger

**Feature Branch**: `021-expenses-payroll-ledger`
**Created**: 2026-01-22
**Status**: Draft
**Input**: Integrated request for expense tracking, job costing, and employee payroll ledger with variable wage models (commission, hourly, daily).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manual Expense Tracking (Priority: P1)

As a Business Owner, I want to record general business expenses (e.g., "Truck repair $200") so that I can track my operational costs independent of specific jobs.

**Why this priority**: Basic expense tracking is the foundation of the system.

**Independent Test**: submitting a text command or form "Add expense - equipment 500$" and verifying it appears in the expense list with the correct amount and category.

**Acceptance Scenarios**:

1. **Given** a business owner is logged in, **When** they input "Add expense: Office Supplies $50", **Then** a new Expense record is created for $50 labeled "Office Supplies".
2. **Given** an existing expense, **When** the owner views the expense report, **Then** the item is listed with date, amount, and description.

---

### User Story 2 - Job-Linked Cost Allocation (Priority: P1)

As a Business Owner, I want to attach expenses to specific jobs or line items (e.g., "Tiles cost $50") so that I can calculate the true profit of a job.

**Why this priority**: Essential for accurate "Per Job" profit reporting.

**Independent Test**: Create a job with $200 revenue, add a linked expense of $50, and verify the job's "Gross Profit" report shows $150.

**Acceptance Scenarios**:

1. **Given** a job worth $500, **When** I add an expense "Materials $100" linked to this job, **Then** the expense is recorded and the Job Profitability view shows $400 net.
2. **Given** a job with a "Window Cleaning" line item, **When** I set a rule "Expense is 30% of Window Cleaning", **Then** the system automatically creates a cost entry calculated from that line item's revenue.

---

### User Story 3 - Employee Wage Calculation (Priority: P1)

As a Business Owner, I want employee wages to be calculated automatically based on their assigned model (Commission, Hourly, or Daily) so that I don't have to do manual math.

**Why this priority**: Reduces administrative burden and errors in payroll.

**Independent Test**: Configure an employee as "Hourly", have them "Check In" and "Check Out" via chat, and verify their Ledger Balance increases by (Hours * Rate).

**Acceptance Scenarios**:

1. **Given** Employee A is on "30% Commission", **When** they complete a $200 job, **Then** $60 is added to their "Balance Owed" ledger.
2. **Given** Employee B is "Hourly per Job", **When** they "Start Job" at 10:00 and "Finish Job" at 11:00 ($20/hr), **Then** $20 is added to their ledger.
3. **Given** an enabled "Tax Set Aside" of 20%, **When** a $100 wage is generated, **Then** the system shows "$80 Net Pay / $20 Tax Hold" in the owner's view (informational only).

---

### User Story 4 - Payroll Ledger & Payouts (Priority: P1)

As a Business Owner, I want to view what I owe each employee and record payouts so I can manage cash flow and clear balances.

**Why this priority**: Completes the cycle from "Earning" to "Paying".

**Independent Test**: View a balance of $500 for an employee, record a "Cash Payout" of $500, and verify the ending balance is $0.

**Acceptance Scenarios**:

1. **Given** an employee has a balance of $1000, **When** I record a payout of $1000, **Then** the balance updates to $0 and a Payout record is created.
2. **Given** multiple unpaid wages, **When** I view the "Payroll Dashboard", **Then** I see a total "Outstanding Payroll" figure.

---

### User Story 5 - Enhanced Employee Workflow (Priority: P2)

As a Field Employee, I want to "Check In" and "Start Job" via text commands so that my time and wages are tracked accurately.

**Why this priority**: Enabler for the Hourly/Daily wage models defined in User Story 3.

**Independent Test**: Send "start job #123" from an employee account and verify the Job status updates to 'In Progress' with a timestamp.

**Acceptance Scenarios**:

1. **Given** I am an employee, **When** I send "Check In", **Then** my "Shift Start" time is recorded.
2. **Given** I am at a job site, **When** I send "Start #123", **Then** the job start time is recorded.

---

### Edge Cases

- **Missed Clocks**: If an employee forgets to "Check In" or "Start Job", the Business Owner must be able to manually insert or edit the time entry to correct the accumulated wage.
- **Rate Changes**: Changing an Employee's wage rate (e.g., from $20/hr to $25/hr) MUST only affect future calculations, preserving the historical ledger values.
- **Negative Balance**: The system should allow "Advance Payments" (Payout > Balance) resulting in a negative balance, which future wages will offset.
- **Deleted Jobs**: If a Job is deleted, linked Expenses should be preserved (orphaned or unlinked) rather than deleted, to maintain financial records.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow creation of `Expense` records with: Amount, Description, Date, Vendor (optional), and Link (Job, LineItem, or General).
- **FR-002**: The `Employee` entity MUST support configuration of a `WageModel`:
  - `COMMISSION_PERCENT` (Apply % to Job Revenue)
  - `HOURLY_PER_JOB` (Paid for time strictly between Start/Finish Job)
  - `HOURLY_PER_SHIFT` (Paid for time between Check-In/Check-Out)
  - `FIXED_DAILY` (Flat rate per day with check-in)
- **FR-003**: The Employee Workflow (Spec 016) MUST accept new commands:
  - `check in` / `start day`: Records shift start.
  - `check out` / `end day`: Records shift end.
  - `start #[ID]`: Records job start timestamp.
- **FR-004**: Completing a job (or shift) MUST trigger a `LedgerEntry` creation that credits the employee's balance based on their `WageModel`.
- **FR-005**: If "Tax Set Aside" is configured, the system MUST calculate and display the estimated tax portion of any wage entry, but DOES NOT deduct it from the ledger (it is informational for the owner).
- **FR-006**: The system MUST support a `Record Payout` action (Manual) that creates a debit `LedgerEntry`, reducing the employee's specific balance.
- **FR-007**: Expenses and Ledger entries MUST be exportable via the existing CSV export framework (Spec 007).
- **FR-008**: Job Profitability calculations MUST deduct linked Expenses and linked Wage Costs from Revenue to show "Net Job Profit".

### Key Entities

- **Expense**: Records a cost. Can be linked to a Job (reducing job profit) or unlinked (operational overhead).
- **LedgerEntry**: A credit (wage earned) or debit (payout) transaction for an Employee.
- **WageConfiguration**: Stores the model (Hourly/Commission) and Rate for an employee.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: "Net Job Profit" is correctly calculated (Revenue - Expenses - Wages) for 100% of jobs with linked costs.
- **SC-002**: Employee "Balance Owed" is accurate within $0.01 based on configured wage rules and logged times.
- **SC-003**: Employee commands `check in` and `start #[ID]` are recognized and timestamped within 2 seconds.
- **SC-004**: Manual Payouts immediately reflect in the employee's running balance.
