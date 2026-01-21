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
2. **Action**: Customer C sends "Where is the technician?" or "ETA".
3. **Result**: System replies "We are approximately 10 minutes away."

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
- **FR-005**: System MUST respond to semantic queries (LLM intent "check_eta" or similar) with the calculated duration.

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
