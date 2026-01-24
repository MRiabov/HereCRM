# Clerk Authentication & User Management

**Status**: Draft
**Feature ID**: 025
**Mission**: software-dev

## Intent Summary

Implement Clerk-based authentication and authorization for HereCRM, modeling Businesses as Organizations and Employees as Users. A key workflow involves handling incoming messages (WhatsApp/SMS) to the CRM: recognized users can interact, while unknown numbers are prompted to register/login via a Clerk link, identifying them as potential business users (not end-customers).

## Context

HereCRM serves Businesses (Tenants).

* **Businesses** are represented as Clerk Organizations.
* **Employees/Owners** are Clerk Users within an Organization.
* **Customers** of the Businesses do **not** register; they are simply Contact records.

The system interacts with users via PWA and messaging channels (WhatsApp/SMS). Communication from the "outside world" to the CRM is assumed to be from authorized Business Users. Unknown senders must be authenticated before allowed to interact.

## Requirements

### Functional Requirements

1. **Clerk Authentication (PWA)**:
    * Secure all `/api/v1/*` endpoints using Clerk JWT verification.
    * Validate session claims (Expiration, Issuer).

2. **Identity Mapping**:
    * Map Clerk `User` to internal `User` entity.
    * Map Clerk `Organization` to internal `Business` (Tenant).
    * Support multiple organizations per user (if Clerk supports it, ensure context switching or default org).

3. **Messaging Ingress & Registration Flow**:
    * **Intercept**: Listen for incoming messages on WhatsApp/SMS channels.
    * **Lookup**: Check if the sender's phone number matches an existing registered `User`.
    * **Unknown Sender**:
        * If the number is not recognized, the system must **not** process the message as a command.
        * Reply with a message: "Welcome to HereCRM. To verify your identity and start using the system, please register here: [Clerk Sign-up Link]".
        * The link should point to the Clerk-hosted (or custom) signup/login flow.
    * **Return to Chat**:
        * After successful registration/login, the user should be guided to return to the messaging app (e.g., via a deep link or "Back to WhatsApp" button on the completion page).

4. **Customer Isolation**:
    * Ensure that "Customers" (contacts of the business) are **never** prompted to register as Users. This flow specifically applies to the "CRM Control" channels, not customer support lines (unless shared, in which case logic must distinguish intent or destination). *Assumption: The number receiving these messages is the CRM System Line, not a specific Business Line, OR the system assumes unmapped numbers on the Business Line are potential new Team Members or errors.* -> **Refinement**: "Only businesses should be able to text with us" implies this is the System Bot.

### Non-Functional Requirements

1. **Security**: Strict separation of duties. Only authenticated Users can access CRM data.
2. **UX**: The transition from Messaging -> Web Auth -> Messaging should be smooth (Deep links where possible).

## User Scenarios

### 1. New Business User via WhatsApp

* **Actor**: New User (Alice).
* **Action**: Alice sends "Hello" to the HereCRM WhatsApp number.
* **System**: Checks DB for Alice's phone number. No match found.
* **System**: Replies "Please register to access HereCRM: [Link]".
* **Actor**: Clicks link, completes Clerk registration (Email/Phone).
* **System**: Webhook/Callback links Alice's Clerk ID to her Phone Number in `users` table.
* **Actor**: Returns to WhatsApp, sends "Hello" again.
* **System**: Recognizes Alice, processes message.

### 2. Existing Employee Login (PWA)

* **Actor**: Employee (Bob).
* **Action**: Opens PWA, enters email/password via Clerk.
* **System**: Validates credentials, issues JWT.
* **System**: Backend verifies JWT on API calls, grants access to Bob's Organization data.

## Success Criteria

1. Unregistered numbers messaging the CRM receive a Signup Link response 100% of the time.
2. Verified Users can interact with the CRM via messaging without re-authentication (using Phone Number as identity key).
3. API requests without valid Clerk tokens return 401 Unauthorized.
4. Internal `User` records correctly link to Clerk IDs.

## Assumptions

1. We are using Clerk's "Organizations" feature for multi-tenancy.
2. The Messaging Provider (Twilio/Meta) sends the sender's phone number reliably.
3. We handle the Clerk `user.created` webhook to sync data to our local DB.
