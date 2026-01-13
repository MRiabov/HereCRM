import hmac
import hashlib
import logging
import sys
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.auth_service import AuthService
from src.services.whatsapp_service import WhatsappService
from src.llm_client import LLMParser
from src.config import settings

router = APIRouter()

# Setup logging
logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    from_number: str
    body: str


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

    # In a real app, LLMParser might take config from env vars
    parser = LLMParser()
    whatsapp_service = WhatsappService(session, parser)

    return auth_service, whatsapp_service


@router.post("/webhook", dependencies=[Depends(verify_signature)])
async def webhook(
    payload: WebhookPayload,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    try:
        auth_service, whatsapp_service = services

        # 1. Identify or Onboard User
        user = await auth_service.get_or_create_user(payload.from_number)

        # 2. Process Message
        response_text = await whatsapp_service.handle_message(
            user_phone=user.phone_number, message_text=payload.body
        )

        # 3. Commit Transaction
        await auth_service.session.commit()

        return {"reply": response_text}

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 Signature)
        raise

    except Exception as e:
        # Log the real error securely
        # Printing to stderr is a simple way to ensure it ends up in logs
        print(f"WEBHOOK ERROR: {str(e)}", file=sys.stderr)
        logger.exception("Webhook processing failed")

        # Return generic error to client
        # We assume 200 OK + error message is better for WhatsApp than 500
        # But for an API, we should probably return 500 if it's a system crash.
        # However, for webhooks, sometimes 200 is needed to stop retries.
        # Let's stick to 500 for now as 'Internal Server Error' is standard.
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
