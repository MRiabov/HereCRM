# HereCRM Backend

HereCRM Backend is a FastAPI service that provides the core logic, LLM processing, and third-party integrations for the HereCRM ecosystem.

## 🚀 Key Responsibilities
- **AI-Powered Extraction**: Parsing natural language from WhatsApp/SMS via GPT-4o.
- **Pipeline Logic**: Automatic progression of customer stages based on job activity.
- **Integrations**: Twilio, Stripe, QuickBooks, Google Calendar, and Geoapify.
- **Multi-Tenancy**: Tenant-isolated data for various businesses.

---

## 🏗️ Architecture
- **Framework**: FastAPI (Python 3.12+)
- **ORM**: SQLAlchemy with `aiosqlite`
- **Migrations**: Alembic
- **Testing**: `pytest` and `schemathesis`

---

## 🛠️ Getting Started

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure environment**:
   Create a `.env` file from the `.env.example`. Key secrets include:
   - `OPENROUTER_API_KEY`
   - `WHATSAPP_APP_SECRET`
   - `DATABASE_URL`

3. **Database Setup**:
   ```bash
   alembic upgrade head
   ```

4. **Run Server**:
   ```bash
   fastapi dev src/main.py
   ```

---

## 🧪 Testing

```bash
pytest
```

---

## 📄 License
Internal Project - All Rights Reserved.
