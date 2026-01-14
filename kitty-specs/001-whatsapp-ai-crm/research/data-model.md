# Data Model: WhatsApp AI CRM

## ER Diagram

```mermaid
erDiagram
    BUSINESS ||--|{ USER : has
    BUSINESS ||--|{ CUSTOMER : owns
    BUSINESS ||--|{ JOB : owns
    BUSINESS ||--|{ REQUEST : owns
    
    USER {
        string id PK
        string phone_number UK
        string business_id FK
        string role "OWNER|MEMBER"
        datetime created_at
    }
    
    BUSINESS {
        string id PK
        string name
        datetime created_at
    }
    
    CUSTOMER {
        string id PK
        string business_id FK
        string name
        string phone_number
        string address
        json metadata
    }
    
    JOB {
        string id PK
        string business_id FK
        string customer_id FK
        string content
        float price
        datetime scheduled_at
        string status "PENDING|DONE|CANCELLED"
    }

    CONVERSATION_STATE {
        string phone_number PK
        string state "IDLE|WAITING_CONFIRM"
        json draft_data
        string last_message_id
        datetime updated_at
    }
```

## Schema Definitions

### ConversationState

Persistence layer for multi-turn dialogues.

- `state`: ENUM.
  - `IDLE`: Ready for new command.
  - `WAITING_CONFIRM`: Tool call generated, waiting for user YES/NO.
  - `WAITING_CLARIF`: Ambiguity resolution needed.
- `draft_data`: JSON blob storing the proposed Tool Call (e.g., `{"tool": "add_job", "args": {...}}`).

### Business Isolation

Every query MUST filter by `business_id` derived from the `User` making the request.

- `User.business_id` is the source of truth.
