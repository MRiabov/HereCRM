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
  - Input: "Add: John, 085 1231234, High Road 34, 50EUR"
  - Action: Create specific Job record linked to Customer (create if new).
  - Extraction: Name, Phone (optional), Location, Price.
  
- **Schedule**:
  - Input: "schedule 085123123 at 14:00" or "schedule High Road 34"
  - Action: Update Job or Customer record with a time/date.
  
- **Store Request**:
  - Input: "Customer called to come later" (implied request)
  - Action: Store as a "Request" item for later triage.

### 2.3. Querying

- **Natural Language Search**:
  - "show jobs for customer with 085 123123"
  - "all customers named John"
  - "requests"
- **Output**: Formatted list of results (concise).

### 2.4. User Experience

- **Feedback**: Every mutating command (Add/Update/Delete) must return a **single-line confirmation**.
  - Example: `✔ Job added: John – High Road 34 – €50`
- **Undo/Edit**: The confirmation response must include options (buttons or text hints) to `Reply: undo | edit`.
- **Undo Action**: Reverts the last operation.

## 3. Data Model (Conceptual)

- **Business**: [ID, Name, CreatedAt]
- **User**: [ID, Phone, Role (Owner/Member), BusinessID]
- **Customer**: [ID, Name, Phone, BusinessID]
- **Job**: [ID, CustomerID, Location, Value, Status, BusinessID]
- **Request**: [ID, Content, Status, BusinessID]
- **Appointment**: [ID, JobID, Time, BusinessID] (or field on Job)

## 4. User Scenarios

### Scenario 1: Zero-Friction Onboarding & Job Entry

1. **User** (new) sends: "Add: Sarah Smith, 555-0100, 123 Maple St, Window Cleaning $150"
2. **System**: Detects new user -> Creates Business -> Creates User -> Creates Customer (Sarah) -> Creates Job.
3. **System** replies: `✔ Job added: Sarah Smith – 123 Maple St – $150`
4. **User** replies: "undo"
5. **System** replies: `All changes reverted.`

### Scenario 2: Team Collaboration

1. **Owner** sends: "Add user 555-0200"
2. **System** adds 555-0200 to Owner's business.
3. **Colleague** (555-0200) sends: "Show all jobs"
4. **System** returns list of jobs created by Owner.

### Scenario 3: Scheduling

1. **User** sends: "Schedule Sarah at 2pm tomorrow"
2. **System** updates Sarah's latest job/record with appointment time 2026-01-14T14:00:00.
3. **System** replies: `✔ Scheduled Sarah Smith for Tomorrow 14:00`

## 5. Success Criteria

- **Parsing Accuracy**: >95% success rate extracting Name, Location, Price from standard "Add: ..." messages.
- **Latency**: End-to-end response time < 3 seconds for standard operations.
- **Isolation**: Users strictly cannot access data from other Businesses.
- **Simplicity**: No "registration forms" or explicit commands needed for onboarding.

## 6. Assumptions & Risks

- **WhatsApp API**: We assume using the existing a WhatsApp webhook setup.
- **LLM Cost**: Per-message LLM processing is acceptable for the business model.
- **Parsing**: Ambiguous inputs will default to "Requests" storage if structured extraction fails.
- **Phone Numbers**: Assumed to be unique identifiers for users.
