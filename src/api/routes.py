import hmac
import hashlib
import logging
import base64
import email.utils
import json

from typing import Tuple, Optional
from twilio.request_validator import RequestValidator

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status, Response, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Message, DocumentType, Customer
from src.services.auth_service import AuthService
from src.services.whatsapp_service import WhatsappService
from src.services.quote_service import QuoteService
from src.llm_client import parser as llm_parser
from src.services.template_service import TemplateService
from src.config import settings
from src.security_utils import check_rate_limit
from src.services.google_calendar_service import GoogleCalendarService
from src.services.analytics import analytics

template_service = TemplateService()

router = APIRouter()
security = HTTPBasic()

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


class GenericWebhookPayload(BaseModel):
    identity: str = Field(..., description="Phone number or email of the CRM user")
    message: str = Field(..., max_length=5000)
    source: str = Field("generic", max_length=100)


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


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
):
    """
    Meta Webhook Verification Challenge.
    """
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook", dependencies=[Depends(verify_signature)])
async def webhook(
    request: Request,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    try:
        auth_service, whatsapp_service = services
        
        # Read body as JSON
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # 1. Handle Real Meta Payload
        if body.get("object") == "whatsapp_business_account":
            processed_count = 0
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    if "messages" in value:
                        for msg in value.get("messages", []):
                            from_number = msg.get("from")  # e.g. "16505551234"
                            msg_type = msg.get("type")
                            
                            # Extract content
                            text_body = ""
                            media_url = None
                            media_type = None
                            
                            if msg_type == "text":
                                text_body = msg.get("text", {}).get("body", "")
                            elif msg_type == "image":
                                media_type = "image"
                                text_body = "[Image]" 
                            else:
                                text_body = f"[{msg_type} message]"
                                
                            # Rate Limit
                            if check_rate_limit(from_number):
                                logger.warning(f"Rate limit exceeded for {from_number}")
                                continue

                            # Get/Create User
                            user, is_new = await auth_service.get_or_create_user(from_number)
                            
                            # Handle Message
                            analytics.capture(
                                user.phone_number or "unknown", 
                                "message_received", 
                                {"body": text_body, "channel": "whatsapp", "is_new_user": is_new}
                            )
                            response_text = await whatsapp_service.handle_message(
                                user_id=user.id,
                                user_phone=user.phone_number,
                                message_text=text_body,
                                is_new_user=is_new,
                                channel="whatsapp",
                                media_url=media_url,
                                media_type=media_type
                            )
                            
                            # Send Reply explicitly via Cloud API
                            if response_text:
                                analytics.capture(
                                    user.phone_number or "unknown", 
                                    "reply_sent", 
                                    {"body": response_text, "channel": "whatsapp"}
                                )
                                from src.services.messaging_service import messaging_service
                                await messaging_service.send_message(
                                    recipient_phone=user.phone_number or "",
                                    content=response_text,
                                    channel="whatsapp",
                                    trigger_source="bot_reply"
                                )
                            
                            processed_count += 1
            
            # Commit transaction for all processed messages
            await auth_service.session.commit()
            return {"status": "ok", "processed": processed_count}

        # 2. Fallback: Stub/Simulator Payload (Flat JSON)
        elif "from_number" in body:
            # Validate using WebhookPayload to enforce constraints (max length, regex)
            try:
                WebhookPayload(**body)
            except Exception as e:
                raise HTTPException(status_code=422, detail=str(e))

            from_number = body.get("from_number")
            text_body = body.get("body", "")
            media_url = body.get("media_url")
            media_type = body.get("media_type")
            
            if check_rate_limit(from_number):
                return {"reply": "Too many requests. Please try again later."}

            user, is_new = await auth_service.get_or_create_user(from_number)
            
            analytics.capture(
                user.phone_number or "unknown", 
                "message_received", 
                {"body": text_body, "channel": "whatsapp_stub", "is_new_user": is_new}
            )
            response_text = await whatsapp_service.handle_message(
                user_id=user.id,
                user_phone=user.phone_number or "unknown",
                message_text=text_body,
                is_new_user=is_new,
                media_url=media_url,
                media_type=media_type,
                channel="whatsapp"
            )
            
            if response_text:
                analytics.capture(
                    user.phone_number or "unknown", 
                    "reply_sent", 
                    {"body": response_text, "channel": "whatsapp_stub"}
                )
            
            await auth_service.session.commit()
            
            # For stub, we return the reply in body (legacy behavior)
            return {"reply": response_text}

        else:
            # Unrecognized format, return 200 to acknowledge webhook (prevent retries) but log warning
            logger.warning(f"Unrecognized webhook format: {body.keys()}")
            return {"status": "ignored"}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Webhook processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Our team has been notified."
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


async def verify_twilio_signature(request: Request):
    """
    Verifies the Twilio signature to ensure requests are coming from Twilio.
    """
    if not settings.twilio_auth_token:
        # If not configured, we might be in dev mode or forgot config.
        # Log error and fail secure.
        logger.error("TWILIO_AUTH_TOKEN is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration Error",
        )
    
    # Get the signature from headers
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Twilio Signature"
        )
    
    # Use Twilio's official RequestValidator
    validator = RequestValidator(settings.twilio_auth_token)
    
    # Get the full URL and form data
    url = str(request.url)
    form_data = await request.form()
    params = dict(form_data)
    
    if not validator.validate(url, params, signature):
        logger.warning("Invalid Twilio webhook signature attempt.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio Signature"
        )
    
    return form_data



@router.post("/webhooks/twilio", dependencies=[Depends(verify_twilio_signature)])
async def twilio_webhook(
    request: Request,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    try:
        auth_service, whatsapp_service = services
        form = await request.form()
        
        from_number = str(form.get("From"))
        body = str(form.get("Body"))
        
        if not from_number or from_number == "None":
            return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")
            
        if body is None or body == "None":
            return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")

        # Rate Limit
        if check_rate_limit(from_number):
             logger.warning(f"Rate limit exceeded for {from_number} (SMS)")
             return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")

        # Get/Create User
        user, is_new = await auth_service.get_or_create_user(from_number)
        
        # Handle Message
        # The reply text is sent via TwilioService inside handle_message for SMS channel
        await whatsapp_service.handle_message(
            user_id=user.id,
            user_phone=user.phone_number,
            message_text=body,
            channel="sms",
            is_new_user=is_new
        )
        
        await auth_service.session.commit()
        
        # Return empty TwiML response as we use the Twilio REST API for replies
        return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")

    except Exception:
        logger.exception("Twilio webhook processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Error"
        )


async def verify_generic_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """
    Verifies the API key for the generic webhook.
    """
    if not settings.generic_webhook_secret:
        logger.error("GENERIC_WEBHOOK_SECRET is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration Error"
        )

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key"
        )

    if not hmac.compare_digest(x_api_key, settings.generic_webhook_secret):
        logger.warning("Invalid Generic Webhook API Key attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )


async def verify_postmark_auth(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    """
    Verifies Basic Auth credentials for Postmark webhooks.
    """
    if not settings.postmark_auth_user or not settings.postmark_auth_pass:
        logger.error("POSTMARK_AUTH_USER or POSTMARK_AUTH_PASS is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration Error",
        )

    # Secure comparison
    is_correct_username = hmac.compare_digest(
        credentials.username.encode("utf8"),
        settings.postmark_auth_user.encode("utf8")
    )
    is_correct_password = hmac.compare_digest(
        credentials.password.encode("utf8"),
        settings.postmark_auth_pass.encode("utf8")
    )

    if not (is_correct_username and is_correct_password):
        logger.warning("Invalid Postmark webhook credentials.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.post("/webhooks/generic", dependencies=[Depends(verify_generic_api_key)])
async def generic_webhook(
    payload: GenericWebhookPayload,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    """
    Generic webhook for external systems (Zapier, etc.)
    """
    try:
        auth_service, whatsapp_service = services

        # Rate Limiting
        if check_rate_limit(payload.identity):
            logger.warning(f"Rate limit exceeded for {payload.identity} (Generic)")
            return {"reply": "Too many requests. Please try again later."}

        # Identify or Onboard User
        user, is_new = await auth_service.get_or_create_user_by_identity(payload.identity)

        # Process Message
        response_text = await whatsapp_service.handle_message(
            user_id=user.id,
            user_phone=user.phone_number,
            message_text=payload.message,
            is_new_user=is_new,
            channel=payload.source
        )

        # Commit Transaction
        await auth_service.session.commit()

        return {
            "reply": response_text,
            "user_id": user.id,
            "status": "processed",
            "source": payload.source
        }

    except Exception:
        logger.exception("Generic webhook processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Error"
        )


class TextGridWebhookPayload(BaseModel):
    from_number: str = Field(..., alias="from")
    to_number: str = Field(..., alias="to")
    text: str


@router.post("/webhooks/textgrid")
async def textgrid_webhook(
    payload: TextGridWebhookPayload,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    """
    Handles inbound SMS from TextGrid.
    Payload expected: {"from": "+123", "to": "+456", "text": "Hello"}
    """
    try:
        auth_service, whatsapp_service = services
        
        # Rate Limiting
        if check_rate_limit(payload.from_number):
            logger.warning(f"Rate limit exceeded for {payload.from_number} (TextGrid)")
            return {"status": "rate_limited"}

        # Identify or Onboard User
        user, is_new = await auth_service.get_or_create_user(payload.from_number)
        
        # Process Message
        # We reuse the WhatsappService handle_message logic but for 'sms' channel
        await whatsapp_service.handle_message(
            user_id=user.id,
            user_phone=user.phone_number,
            message_text=payload.text,
            is_new_user=is_new,
            channel="sms"
        )
        
        # Commit Transaction
        await auth_service.session.commit()
        
        return {"status": "success"}

    except Exception:
        logger.exception("TextGrid webhook processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Error"
        )




@router.post("/webhooks/postmark/inbound", dependencies=[Depends(verify_postmark_auth)])
async def postmark_inbound_webhook(
    request: Request,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    """
    Handles inbound email messages from Postmark.
    Postmark sends JSON payload with email details.
    """
    try:
        auth_service, whatsapp_service = services
        # Parse JSON payload from Postmark
        payload = await request.json()
        
        # Extract email fields
        raw_from = payload.get("From", "")
        _, from_email = email.utils.parseaddr(raw_from)
        subject = payload.get("Subject", "")
        text_body = payload.get("TextBody", "")
        
        # Extract threading headers for conversation continuity
        message_id = payload.get("MessageID", "")
        in_reply_to = payload.get("Headers", [])
        references = None
        in_reply_to_value = None
        
        # Parse headers array to extract In-Reply-To and References
        for header in in_reply_to if isinstance(in_reply_to, list) else []:
            if header.get("Name") == "In-Reply-To":
                in_reply_to_value = header.get("Value")
            elif header.get("Name") == "References":
                references = header.get("Value")
        
        if not from_email or not text_body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: From or TextBody"
            )
        
        # Rate limiting
        if check_rate_limit(from_email):
            logger.warning(f"Rate limit exceeded for {from_email}")
            return {"status": "rate_limited"}
        
        # Get or create user by email
        user, is_new = await auth_service.get_or_create_user_by_identity(from_email)
        
        # Ensure user has an email (it should always have one at this point)
        user_identifier = user.email or from_email

        # Handle Attachments (WP05)
        attachments = payload.get("Attachments", [])
        if attachments:
            from src.services.document_service import DocumentService
            from src.repositories import CustomerRepository
            
            customer_repo = CustomerRepository(auth_service.session)
            # Try to find customer by email
            customer = await customer_repo.get_by_email(from_email, user.business_id)
            
            if not customer:
                # If no customer exists, we create one to attach documents to.
                # Use name from email if possible, or fallback
                # Postmark "From" might correspond to "Name <email>" but here we have parsed 'from_email' which is just email?
                # Actually line 489: from_email = payload.get("From", "") 
                # Postmark "From" is usually "Full Field". 
                # The code used `auth_service.get_or_create_user_by_identity` which handles parsing maybe?
                # Let's assume from_email is the address for now, or check if it needs parsing.
                # `auth_service.get_or_create_user_by_identity` is robust.
                
                # We'll create a customer with available info
                clean_name = from_email.split("<")[0].strip().replace('"','') if "<" in from_email else from_email.split("@")[0]
                # If from_email has angle brackets, we should probably extract the email part for the field `email`.
                # But let's assume `get_by_email` expects the actual email.
                
                # Simplified creation:
                customer = Customer(
                    business_id=user.business_id,
                    name=clean_name or "New Customer",
                    email=from_email if "@" in from_email else None, # Rough check
                    pipeline_stage="contacted"
                )
                customer_repo.add(customer)
                await auth_service.session.flush()
            
            document_service = DocumentService(auth_service.session)
            for attachment in attachments:
                name = attachment.get("Name")
                content_b64 = attachment.get("Content")
                content_type = attachment.get("ContentType")
                
                if name and content_b64:
                    try:
                        file_bytes = base64.b64decode(content_b64)
                        await document_service.create_document(
                            customer_id=customer.id,
                            file_obj=file_bytes,
                            filename=name,
                            mime_type=content_type,
                            doc_type=DocumentType.CUSTOMER_UPLOAD
                        )
                    except Exception as e:
                        logger.error(f"Failed to process attachment {name}: {e}")
                        # Continue with other attachments

        
        # Process message using WhatsappService (unified message handling)
        response_text = await whatsapp_service.handle_message(
            user_id=user.id,
            user_phone=user_identifier,  # Using email as identifier
            message_text=text_body,
            is_new_user=is_new,
            channel="email"
        )
        
        # Store threading metadata in the most recent message
        # Query the last message for this user directly via session
        from sqlalchemy import desc
        query = (
            select(Message)
            .where(Message.user_id == user.id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        result = await auth_service.session.execute(query)
        last_message = result.scalar_one_or_none()
        
        if last_message:
            meta = last_message.log_metadata
            if meta is None:
                meta = {}
            
            meta["email_message_id"] = message_id
            if in_reply_to_value:
                meta["in_reply_to"] = in_reply_to_value
            if references:
                meta["references"] = references
            
            last_message.log_metadata = meta
        
        # Commit transaction
        await auth_service.session.commit()
        
        # Send response via Postmark
        from src.services.postmark_service import PostmarkService
        postmark_service = PostmarkService()
        
        # Prepare reply subject
        reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"
        
        await postmark_service.send_email(
            to_email=from_email,
            subject=reply_subject,
            body=response_text,
            in_reply_to=message_id,  # Reply to the incoming message
            references=f"{references} {message_id}" if references else message_id
        )

        
        return {
            "status": "success",
            "message": "Email processed"
        }
        
    except HTTPException:
        raise
    
    except Exception:
        logger.exception("Postmark webhook processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred."
        )

@router.post("/quotes/{token}/confirm")
async def confirm_quote(
    token: str,
    services: Tuple[AuthService, WhatsappService] = Depends(get_services),
):
    """
    Public endpoint to confirm a quote via token.
    """
    auth_service, _ = services
    quote_service = QuoteService(auth_service.session)
    
    quote = await quote_service.confirm_quote(token)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Quote not found or invalid token"
        )
    
    # Notify business owner / customer about confirmation?
    # For now just return success JSON
    return {"status": "success", "message": "Quote accepted", "quote_id": quote.id, "job_id": quote.job_id}


@router.get("/webhooks/quickbooks/callback")
async def quickbooks_callback(
    code: str = Query(...),
    state: str = Query(...),
    realmId: str = Query(None), # QuickBooks passes 'realmId' param
    db: AsyncSession = Depends(get_db),
):
    """
    Handle OAuth callback from QuickBooks.
    Exchanges code for tokens and updates DB.
    """
    try:
        from src.services.accounting.quickbooks_auth import QuickBooksAuthService
        auth_service = QuickBooksAuthService(db)
        
        # realmId is mandatory for QB Online but optional for Payments API (though we use Online)
        if not realmId:
             raise HTTPException(status_code=400, detail="Missing realmId")

        await auth_service.handle_callback(code, realmId, state)
        
        return {"status": "success", "message": "QuickBooks connected successfully! You can close this window."}
    except Exception as e:
        logger.error(f"QuickBooks callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.get("/auth/google/login")
async def google_login(
    user_id: int,
):
    """
    Redirects user to Google OAuth login page.
    """
    try:
        service = GoogleCalendarService()
        # In a real app, we should sign the state to prevent tampering
        auth_url, _ = service.get_auth_url(state=str(user_id))
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Google login failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    success_url: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle OAuth callback from Google.
    Exchanges code for tokens and updates User in DB.
    """
    try:
        # Try to parse state as JSON (new style) or int (legacy style)
        try:
            state_data = json.loads(state)
            user_id = int(state_data.get("user_id"))
            # If success_url was passed in state, it overrides the query param
            if "success_url" in state_data:
                success_url = state_data["success_url"]
        except (json.JSONDecodeError, TypeError, ValueError):
            user_id = int(state)
        
        service = GoogleCalendarService()
        success = await service.process_auth_callback(code, user_id, db)
        if success:
            # Notify User
            from src.services.messaging_service import messaging_service
            from src.repositories import UserRepository
            
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            
            if user and user.phone_number:
                # Send async notification
                await messaging_service.send_message(
                    recipient_phone=user.phone_number,
                    content="✔ Google Calendar connected! Your assigned jobs will now appear on your calendar.",
                    channel=user.preferred_channel or "whatsapp",
                    trigger_source="system_notification"
                )

            await db.commit()

            if success_url:
                return RedirectResponse(url=success_url)
            
            # Return nice HTML
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Connected</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; text-align: center; padding: 40px; background-color: #f4f4f5; color: #18181b; }
                    .container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); max-width: 400px; margin: 0 auto; }
                    h1 { color: #10b981; margin-bottom: 16px; font-size: 24px; }
                    p { color: #52525b; line-height: 1.5; margin-bottom: 24px; }
                    .icon { font-size: 48px; margin-bottom: 16px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">📅</div>
                    <h1>Connected!</h1>
                    <p>Google Calendar has been successfully linked. Your assigned jobs will now automatically appear on your calendar.</p>
                    <p style="font-size: 14px; color: #71717a;">You can close this window now.</p>
                </div>
            </body>
            </html>
            """
            return Response(content=html_content, media_type="text/html")
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.exception(f"Google callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")
