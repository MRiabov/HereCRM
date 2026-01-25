from datetime import datetime
import os
from src.llm_client import parser
from src.tool_executor import ToolExecutor
from src.services.template_service import TemplateService
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.messaging_service import messaging_service
from src.services.whatsapp_service import WhatsappService
from src.schemas.pwa import ChatMessage, ChatSendRequest
from src.models import Message, MessageRole, User, Service
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

async def get_crm_service(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CRMService:
    return CRMService(session, business_id=current_user.business_id)

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
    current_user: User = Depends(get_current_user),
    service: CRMService = Depends(get_crm_service)
):
    print(f"DEBUG: Processing send_message for customer_id={request.customer_id} business_id={service.business_id}")
    
    # Handle AI Assistant Chat (customer_id=0)
    if request.customer_id == 0:
        # 1. Parse using LLM
        system_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Fetch service catalog for context
        catalog_stmt = select(Service).where(Service.business_id == service.business_id)
        catalog_result = await service.session.execute(catalog_stmt)
        services_list = catalog_result.scalars().all()
        service_catalog = "\n".join([f"- {s.name}: €{s.default_price}" for s in services_list])
        
        user_context = {
            "role": current_user.role,
            "name": current_user.name,
            "business_id": current_user.business_id
        }

        tool_call = await parser.parse(
            text=request.message,
            system_time=system_time,
            service_catalog=service_catalog,
            user_context=user_context
        )

        if tool_call is None:
            # Try direct completion
            response_text = await parser.chat_completion([
                {"role": "system", "content": "You are a helpful CRM assistant. Respond concisely."},
                {"role": "user", "content": request.message}
            ])
            return {"status": "sent", "content": response_text}

        if isinstance(tool_call, str):
            return {"status": "sent", "content": tool_call}

        # 2. Execute tool
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompts_path = os.path.join(base_dir, "assets", "prompts.yaml")
        template_service = TemplateService(yaml_path=prompts_path)
        
        executor = ToolExecutor(
            session=service.session,
            business_id=service.business_id,
            user_id=current_user.id,
            user_phone=current_user.phone_number or "",
            template_service=template_service
        )
        
        response_text, _ = await executor.execute(tool_call)
        
        # Commit changes made by tool
        await service.session.commit()
        
        return {"status": "sent", "content": response_text}

    customer = await service.customer_repo.get_by_id(request.customer_id, service.business_id)
    if not customer:
        print(f"DEBUG: Customer {request.customer_id} not found for business {service.business_id}")
        raise HTTPException(status_code=404, detail=f"Customer {request.customer_id} not found")
    if not customer.phone:
        print(f"DEBUG: Customer {request.customer_id} has no phone")
        raise HTTPException(status_code=404, detail="Customer has no phone number")
        
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
