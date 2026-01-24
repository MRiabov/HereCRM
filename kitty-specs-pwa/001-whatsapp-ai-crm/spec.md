# Feature Specification: PWA AI CRM

**Feature**: PWA AI CRM
**Status**: Draft
**Mission**: software-dev

## 1. Overview

A lightning-fast, text-first CRM living entirely within a Progressive Web App (PWA). It is designed for busy individuals and small teams to manage jobs, customers, and schedules using natural language commands. The system is multi-tenant, allowing business owners to onboard themselves and invite team members by phone number or email.

## 2. Functional Requirements

### 2.0. Interface Structure
- **Chat-First UI**: The core experience mimics a chat application.
- **Side Menu**: A collapsible left-hand menu provides quick access to visual tools (e.g., Pipeline Board, Map View, Calendar, Settings).


### 2.1. Onboarding & Auth

- **Self-Serve Creation**: The first time a phone number logs in or visits the PWA, check if it belongs to an existing business. If not, create a new "Business" entity and make this user the Owner.
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
    - "Search within 1km of High Street 34, Dublin" (using OpenStreetMap Geocoding)
- **Output**: Formatted list of results (concise).

### 2.4. User Experience

- **Feedback**: Every mutating command (Add/Update/Delete) must return a **single-line confirmation**.
  - Example: `✔ Job added: John – High Road 34 – €50`
- **Undo/Edit**: The confirmation response must include options (buttons or text hints) to `Click 'Undo' or 'Edit' (or type commands).
- **Undo Action**: Reverts the last operation.
- **Edit Last Action**: Prompt the user to edit the last successful job, customer, or request. Example reply: `Edit the last job (John, 50$, No location). Type the job or customer details as you would before.`
- **Configurable Messaging**: All system-generated messages sent to customers must be configurable via a YAML file to allow easy text editing without code changes. These messages support variable interpolation using `{}` or `{{}}` syntax.

### 2.5. Security & Safety

- **Rate Limiting**: The system must include rate limiting on the API endpoint to prevent denial-of-service and LLM credit exhaustion.
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

1. **User** (new) types: "Add: Sarah Smith, 555-0100, 123 Maple St, Window Cleaning $150"
2. **System**: Detects new user -> Creates Business -> Creates User -> Creates Customer (Sarah) -> Creates Job.
3. **System** displays: `✔ Job added: Sarah Smith – 123 Maple St – $150`
4. **User** types: "undo"
5. **System** displays: `All changes reverted.`

### Scenario 1b: Edit Last

1. **User** types: "Add: John, 50$"
2. **System** displays: `✔ Job added: John – No location – €50.0 (Click 'Undo' or 'Edit' (or type commands).
3. **User** types: "edit last"
4. **System** displays: `Edit the last job (John, 50$, No location). Type the job or customer details as you would before.`

### Scenario 2: Team Collaboration

1. **Owner** types: "Add user 555-0200"
2. **System** adds 555-0200 to Owner's business.
3. **Colleague** (555-0200) types: "Show all jobs"
4. **System** returns list of jobs created by Owner.

### Scenario 3: Scheduling & Requests

1. **User** types: "add request: Sarah wanted her windows cleaned, 12 windows"
2. **System** creates a Request for Sarah.
3. **System** displays: `✔ Request stored: Sarah wanted her windows cleaned`
4. **User** types: "schedule Sarah at 2pm tomorrow"
5. **System** updates Sarah's latest job/record with appointment time 2026-01-14T14:00:00.
6. **System** displays: `✔ Scheduled Sarah Smith for Tomorrow 14:00`

## 5. Success Criteria

- **Parsing Accuracy**: >95% success rate extracting Name, Location, Price from standard "Add: ..." messages.
- **Latency**: End-to-end response time < 3 seconds for standard operations.
- **Isolation**: Users strictly cannot access data from other Businesses.
- **Simplicity**: No "registration forms" or explicit commands needed for onboarding.

## 6. Assumptions & Risks

- Backend API: We assume using the existing API endpoint setup.
- **LLM Cost**: Per-message LLM processing is acceptable for the business model.
- **Parsing**: If structured extraction fails, the system will respond with a "Sorry, we couldn't understand your request" message followed by a help guide, rather than storing it as a Request.
- **Phone Numbers**: Assumed to be unique identifiers for users.
