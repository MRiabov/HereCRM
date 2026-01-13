from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.auth_service import AuthService
from src.services.whatsapp_service import WhatsappService
from src.llm_client import LLMParser
from typing import Tuple

router = APIRouter()


class WebhookPayload(BaseModel):
    from_number: str
    body: str


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


@router.post("/webhook")
async def webhook(
    payload: WebhookPayload,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    auth_service, whatsapp_service = services

    # 1. Identify or Onboard User
    try:
        user = await auth_service.get_or_create_user(payload.from_number)
    except Exception as e:
        # Log error in real life
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")

    # 2. Process Message
    # Note: handle_message will re-fetch the user/state internally.
    # Logic flow: Webhook -> Auth (ensures User exists) -> Service (does the work)
    response_text = await whatsapp_service.handle_message(
        user_phone=user.phone_number, message_text=payload.body
    )

    # 3. Commit Transaction
    # Modifications (new User, new Business, State updates) happen in the session.
    # We commit here at the end of the request.
    await auth_service.session.commit()

    return {"reply": response_text}
