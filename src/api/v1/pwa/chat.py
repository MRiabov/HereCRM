from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.messaging_service import messaging_service
from src.schemas.pwa import ChatMessage, ChatSendRequest
from src.models import Message, MessageRole

router = APIRouter()

async def get_crm_service(session: AsyncSession = Depends(get_db)) -> CRMService:
    return CRMService(session, business_id=1)

@router.get("/history/{customer_id}", response_model=List[ChatMessage])
async def get_chat_history(
    customer_id: int,
    service: CRMService = Depends(get_crm_service)
):
    # 1. Get Customer to find phone number/User ID
    customer = await service.customer_repo.get_by_id(customer_id, service.business_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    phone = customer.phone
    if not phone:
        return []

    # 2. Query messages by phone
    # Ideally we should link Customer -> User -> Messages but phone is the common key usually
    stmt = (
        select(Message)
        .where(
            (Message.from_number == phone) | (Message.to_number == phone),
            Message.business_id == service.business_id
        )
        .order_by(Message.created_at.asc())
    )
    result = await service.session.execute(stmt)
    messages = result.scalars().all()
    
    return [
        ChatMessage(
            role=msg.role,
            content=msg.body,
            timestamp=msg.created_at,
            is_outbound=(msg.role == MessageRole.ASSISTANT)
        )
        for msg in messages
    ]

@router.post("/send")
async def send_message(
    request: ChatSendRequest,
    service: CRMService = Depends(get_crm_service)
):
    customer = await service.customer_repo.get_by_id(request.customer_id, service.business_id)
    if not customer or not customer.phone:
        raise HTTPException(status_code=404, detail="Customer not found or no phone number")
        
    # Send via MessagingService
    # Assuming 'whatsapp' as default for now or check customer preference
    # The 'messaging_service' is a global instance imported
    
    await messaging_service.send_message(
        recipient_phone=customer.phone,
        content=request.message,
        channel="whatsapp", # TODO: Dynamic channel selection
        trigger_source="pwa_chat_manual"
    )
    
    return {"status": "sent"}
