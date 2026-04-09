# Feature Specification: Google Calendar Integration

**Feature**: Google Calendar Integration
**Status**: Draft
**Mission**: software-dev

## 1. Overview

This feature provides an optional, one-way synchronization of scheduled jobs from the CRM to a user's personal Google Calendar. It allows field workers and business owners to view their daily schedule natively in their calendar apps. Authorization is handled individually per user via the settings menu.

## 2. Functional Requirements

### 2.0. Interface Structure
- **Chat-First UI**: The core experience mimics a chat application.
- **Side Menu**: A collapsible left-hand menu provides quick access to visual tools (e.g., Pipeline Board, Map View, Calendar, Settings).


### 2.1. Authentication & Connection

- **Individual Auth**: Each user ("Owner" or "Member") creates their own link to their personal Google Calendar. The business does not share a single calendar.
- **Settings Integration**: The connection flow is initiated from the existing conversational Workflow Settings (defined in Spec 19).
- **OAuth Flow**:
  - User sends command: "Connect Google Calendar"
  - System generates a unique, user-specific OAuth URL.
  - User completes flow in browser.
  - User receives an auth code or success screen.
  - System stores the **refresh token** securely against the `User` record.

### 2.2. Synchronization Logic (One-Way)

- **Direction**: STRICT One-Way (CRM → Google Calendar). Changes made in Google Calendar are **NOT** reflected in the CRM.
- **Trigger**: An event is upserted (created or updated) in Google Calendar when:
  1. A Job is **assigned** to a User AND has a **scheduled time**.
  2. A Job's details (time, location, description) are updated.
  3. A Job is reassigned (remove from old user's calendar, add to new user's calendar).
- **Assignment Defaults**:
  - If a business has only one user (Owner), jobs are auto-assigned to them.
  - If a business has multiple users, jobs must be explicitly assigned to appear.
- **Event Content**:
  - **Title**: `Job for [Client Name] - [Service/Description]`
  - **Location**: Client Address (City, Street, etc.)
  - **Time**: Job Start Time (Duration defaults to 1 hour if not specified, or based on system defaults).
  - **Description**: Standard `job_summary` template (Client Name, Phone, Address, Job Description, Lines).

### 2.3. User Experience

- **Connect**:
  - Input: "Connect calendar"
  - Response: "Please visit this link to authorize Google Calendar: [Link]"
- **Disconnect**:
  - Input: "Disconnect calendar"
  - Response: "Calendar disconnected. Future jobs will not sync."
- **Status**:
  - "Show settings" output includes: `• Google Calendar: Connected (user@gmail.com)` or `Not Connected`.

### 2.4. Error Handling

- **Auth Failures**: Explain clearly if permissions were denied.
- **Sync Failures**: If a token expires or is revoked, log the error and flag the user status as "Needs Re-auth" without crashing the job creation flow.
- **Rate Limiting**: Respect Google API quotas.

## 3. Data Model (Conceptual)

### 3.1. User Entity Updates

- `google_calendar_credentials`: JSON field to store:
  - `refresh_token`
  - `access_token` (ephemeral)
  - `calendar_id` (default to 'primary')
  - `connected_at` (timestamp)
- `google_calendar_sync_enabled`: Boolean

### 3.2. Job/Appointment Entity Updates

- `gcal_event_id`: Store the Google Calendar Event ID to allow updates/deletions.
  - *Note*: If a job is reassigned, this ID is used to delete the event from the old user's calendar.

## 4. User Scenarios

### Scenario 1: Initial Connection

1. **User** (Member) types: "Connect Google Calendar"
2. **System** displays: "Click here to authorize: <https://accounts.google.com/>..."
3. **User** clicks, authorizes.
4. **System** confirms: "✔ Google Calendar connected! Your assigned jobs will now appear on your calendar."

### Scenario 2: Scheduling a Job (One-Way Sync)

1. **Owner** types: "Schedule Job #123 for John at 2pm tomorrow"
2. **System** updates Job #123:
   - Assigns to John.
   - Sets time to Tomorrow 2pm.
3. **System** detects John has GCal connected.
4. **System** creates GCal Event:
   - **Title**: "Job for Sarah Smith"
   - **Time**: Tomorrow 2pm - 3pm
   - **Loc**: "123 Maple St"
5. **System** displays: "✔ Job #123 assigned to John for Tomorrow 2pm. (Synced to Calendar)"

### Scenario 3: Reassignment

1. **Owner** types: "Reassign #123 to Mary"
2. **System** checks John's GCal -> Deletes Event `abc12345`.
3. **System** checks Mary's GCal -> Creates Event `xyz9876`.
4. **System** displays: "✔ Job #123 reassigned to Mary."

## 5. Success Criteria

- **Auth**: Users can successfully link and unlink their personal Google account.
- **Accuracy**: Job details (Time, Location, Client) in GCal match CRM data exactly.
- **Updates**: Changing a job time in CRM updates the GCal event within 10 seconds.
- **Reassignment**: Jobs correctly move from User A's calendar to User B's calendar upon reassignment.
- **Resiliance**: Job creation takes precedence; GCal errors do not block CRM operations.

## 6. Assumptions & Risks

- **Assumption**: Users have a Google Account.
- **Assumption**: We verify the "primary" calendar is writable.
- **Risk**: Google API Rate Limits (mitigated by background processing/queues if scale increases).
- **Risk**: Token expiry (requires re-auth flow).
