import logging
import os
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from src.database import get_db
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clerk", tags=["webhooks"])

@router.post("")
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle webhooks from Clerk.
    """
    webhook_secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.error("CLERK_WEBHOOK_SECRET is not set")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        logger.warning(f"Missing svix headers: id={svix_id}, timestamp={svix_timestamp}, signature={svix_signature}")
        raise HTTPException(status_code=400, detail="Missing svix headers")

    payload = await request.body()
    
    # Verify signature
    try:
        wh = Webhook(webhook_secret)
        headers = {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        }
        event = wh.verify(payload, headers)
    except WebhookVerificationError:
        logger.warning("Invalid svix signature for Clerk webhook")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error verifying Clerk webhook: {e}")
        raise HTTPException(status_code=400, detail="Error verifying webhook")

    event_type = event.get("type")
    data = event.get("data")
    
    auth_service = AuthService(db)
    
    try:
        if event_type in ["user.created", "user.updated"]:
            await auth_service.sync_clerk_user(data)
        elif event_type in ["organization.created", "organization.updated"]:
            await auth_service.sync_clerk_org(data)
        elif event_type == "organizationMembership.created":
            await auth_service.sync_clerk_membership(data)
        else:
            logger.info(f"Unhandled Clerk event type: {event_type}")
            
        await db.commit()
    except Exception as e:
        logger.error(f"Error processing Clerk webhook {event_type}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal processing error")

    return {"status": "SUCCESS"}
