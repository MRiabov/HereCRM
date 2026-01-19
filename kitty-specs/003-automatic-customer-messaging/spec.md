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
