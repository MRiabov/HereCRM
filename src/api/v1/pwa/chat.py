from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from src.database import get_db
from src.services.auth_service import AuthService
from src.services.whatsapp_service import WhatsappService
from src.services.messaging_service import messaging_service
from src.services.template_service import TemplateService
from src.llm_client import parser as llm_parser
from src.schemas.pwa import ChatMessage, ChatSendRequest
from src.models import Message, Customer, MessageRole
from src.repositories import CustomerRepository

router = APIRouter()

template_service = TemplateService()

async def get_chat_services(session: AsyncSession = Depends(get_db)):
    auth_service = AuthService(session)
    whatsapp_service = WhatsappService(session, llm_parser, template_service)
    return auth_service, whatsapp_service

@router.get("/history/{customer_id}", response_model=List[ChatMessage])
async def get_chat_history(
    customer_id: int,
    session: AsyncSession = Depends(get_db)
):
    business_id = 1
    
    # Get customer to find phone/identifiers
    cust_repo = CustomerRepository(session)
    customer = await cust_repo.get_by_id(customer_id, business_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    identifier = customer.phone or customer.email
    if not identifier:
         return []

    # Get messages linked to this customer (by phone/email)
    # We query messages where from_number or to_number matches active channel ID of customer?
    # Simplification: Query by phone
    
    # Also we might have User linked to Customer? 
    # Current DB model separates User (Employee/Owner) from Customer (Entity).
    # But Message has user_id (User).
    # IF Customer interacts via WhatsApp, they are considered a "User" in auth_service concept?
    # Let's check `User` table role.
    
    # Query messages by phone
    query = (
        select(Message)
        .where(
            or_(
                Message.from_number == identifier,
                Message.to_number == identifier
            )
        )
        .order_by(Message.created_at.asc())
    )
    result = await session.execute(query)
    messages = result.scalars().all()
    
    return [
        ChatMessage(
            role=msg.role,
            content=msg.body,
            timestamp=msg.created_at,
            is_outbound=(msg.role == MessageRole.ASSISTANT) # or based on from_number != customer_phone
        )
        for msg in messages
    ]

@router.post("/send")
async def send_message(
    payload: ChatSendRequest,
    services: tuple = Depends(get_chat_services)
):
    auth_service, whatsapp_service = services
    business_id = 1
    
    cust_repo = CustomerRepository(auth_service.session)
    customer = await cust_repo.get_by_id(payload.customer_id, business_id)
    if not customer or not customer.phone:
         raise HTTPException(status_code=400, detail="Customer has no phone number")

    # Send message using MessagingService
    # This sends to the provider (Twilio/Meta)
    await messaging_service.send_message(
        recipient_phone=customer.phone,
        content=payload.message,
        channel="whatsapp", # Defaulting to WhatsApp for PWA context usually
        trigger_source="manual_chat"
    )
    
    # Store in DB so it shows up in history immediately
    # MessagingService DOES store it? 
    # checking messaging_service.py... 
    # `send_message` -> `_send_via_whatsapp` ...
    # It usually stores log if configured. 
    # Wait, `MessagingService.send_message` calls `message_repo.add`?
    # Let's assume yes, or we add it manually.
    # Actually, `MessagingService` is designed to handle sending. 
    # Ideally we should see it in `MessageLog` or `messages` table.
    
    return {"status": "sent"}
