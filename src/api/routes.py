import hmac
import hashlib
import logging
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Message
from src.services.auth_service import AuthService
from src.services.whatsapp_service import WhatsappService
from src.llm_client import parser as llm_parser
from src.services.template_service import TemplateService
from src.config import settings
from src.security_utils import check_rate_limit

template_service = TemplateService()

router = APIRouter()

# Setup logging
logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    from_number: str = Field(..., max_length=20, pattern=r"^\+?[1-9]\d{1,14}$")
    body: str = Field(..., max_length=1000)
    media_url: str = Field("", max_length=500)
    media_type: str = Field("", max_length=50)

    @field_validator("from_number", mode="before")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        if isinstance(v, str):
            # Strip spaces, dashes, and parentheses
            return "".join(c for c in v if c.isdigit() or c == "+")
        return v


async def verify_signature(request: Request, x_hub_signature_256: str = Header(None)):
    """
    Verifies the HMAC SHA256 signature from WhatsApp.
    This protects against spoofed requests.
    """
    if not settings.whatsapp_app_secret:
        # In case secret is missing, we fail securely
        logger.error("WHATSAPP_APP_SECRET is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration Error",
        )

    if not x_hub_signature_256:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Signature"
        )

    # Calculate signature
    body_bytes = await request.body()
    secret_bytes = settings.whatsapp_app_secret.encode("utf-8")

    expected_signature = hmac.new(secret_bytes, body_bytes, hashlib.sha256).hexdigest()

    # WhatsApp sends "sha256=<sig>", we usually just get the raw header.
    # If the header includes prefix, handle it. Standard is often just the hash or 'sha256=...'
    # Let's assume standard webhook format 'sha256=...'

    incoming_sig = x_hub_signature_256
    if incoming_sig.startswith("sha256="):
        incoming_sig = incoming_sig[7:]

    if not hmac.compare_digest(incoming_sig, expected_signature):
        logger.warning("Invalid webhook signature attempt.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Signature"
        )


async def get_services(
    session: AsyncSession = Depends(get_db),
) -> Tuple[AuthService, WhatsappService]:
    """
    Dependency to instantiate services with the DB session.
    """
    auth_service = AuthService(session)

    # Use singleton parser and template service
    whatsapp_service = WhatsappService(session, llm_parser, template_service)

    return auth_service, whatsapp_service


@router.post("/webhook", dependencies=[Depends(verify_signature)])
async def webhook(
    payload: WebhookPayload,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    try:
        auth_service, whatsapp_service = services

        # 1. Rate Limiting
        if check_rate_limit(payload.from_number):
            masked_phone = (
                payload.from_number[:3] + "****" + payload.from_number[-2:]
                if len(payload.from_number) > 5
                else "***"
            )
            logger.warning(f"Rate limit exceeded for {masked_phone}")
            return {"reply": "Too many requests. Please try again later."}

        # 2. Identify or Onboard User
        user, is_new = await auth_service.get_or_create_user(payload.from_number)

        # 2. Process Message
        response_text = await whatsapp_service.handle_message(
            user_phone=user.phone_number,
            message_text=payload.body,
            is_new_user=is_new,
            media_url=payload.media_url,
            media_type=payload.media_type,
        )

        # 3. Commit Transaction
        await auth_service.session.commit()

        return {"reply": response_text}

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 Signature)
        raise

    except Exception:
        logger.exception("Webhook processing failed")

        # Return generic error to client
        # We assume 200 OK + error message is better for WhatsApp than 500
        # But for an API, we should probably return 500 if it's a system crash.
        # However, for webhooks, sometimes 200 is needed to stop retries.
        # Let's stick to 500 for now as 'Internal Server Error' is standard.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Our team has been notified.",
        )


@router.get("/history/{phone_number}")
async def get_history(
    phone_number: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the message history for a given phone number.
    """
    # Try to find user to get more accurate history
    from src.repositories import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_phone(phone_number)
    
    if user:
        query = (
            select(Message)
            .where((Message.user_id == user.id) | (Message.from_number == phone_number) | (Message.to_number == phone_number))
            .order_by(Message.created_at.asc())
        )
    else:
        query = (
            select(Message)
            .where((Message.from_number == phone_number) | (Message.to_number == phone_number))
            .order_by(Message.created_at.asc())
        )
    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        {
            "role": msg.role,
            "content": msg.body,
            "timestamp": msg.created_at.isoformat(),
            "metadata": msg.log_metadata
        }
        for msg in messages
    ]
