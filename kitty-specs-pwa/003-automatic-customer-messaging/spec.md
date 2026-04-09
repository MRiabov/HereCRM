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
     - **Quotes**: Triggered when a quote is generated.
     - **Daily Schedule**: Automated "Scheduled Today" messages.
3. **AI-Driven "Smart Follow-up" Engine**:
   - **Trigger**: Quote remains in `SENT` status for a configurable period (default: 48 hours).
   - **Action**: LLM analyzes the quote context and drafts a personalized follow-up message.
   - **User Approval**: The system presents the draft to the business owner for approval and sending.
   - **Configurability**:
     - Enable/disable follow-up engine.
     - Configure the delay period (e.g., 24h, 48h, 72h).
4. **Review & Reputation Management**:
   - **Trigger**: Job is marked as `PAID`.
   - **Wait Time**: 2 hours (configurable).
   - **Action**: Automatically sent a follow-up asking for a review (Google/Yelp link).
   - **User Value**: Automates getting consistent reviews without manual effort.

## Architecture

- **Event Bus Integration**: Subscribes to `QUOTE_SENT` and `JOB_PAID`.
- **Scheduled Tasks**: A background worker (or `MessageQueue` consumer) handles the delay logic (48h for quotes, 2h for reviews).
- **LLM Integration**: For generating personalized follow-up drafts.
- **Queue**: Async message queue for processing and sending messages.
- **Decoupled event subscribers**: Consistent with the current messaging architecture.

## User Interface

- **Approval Dashboard**: A view or chat-based interaction to approve/edit/send AI-generated follow-up drafts.
- **Settings**:
  - Global toggle for "Smart Follow-up".
  - Configurable "Follow-up Delay" (hours/days).
  - Global toggle for "Review Requests".
  - Configurable "Review Link" (Google, Yelp, etc.).
- Business users trigger ad-hoc messages (like "On my way") via the CRM interface (WhatsApp/Chat).
- Configuration for enabling/disabling SMS vs WhatsApp.
