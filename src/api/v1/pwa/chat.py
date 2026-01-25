from datetime import datetime
import os
from src.llm_client import parser
from src.tool_executor import ToolExecutor
from src.services.template_service import TemplateService
from src.services.help_service import HelpService
from src.services.geocoding import GeocodingService
from src.uimodels import HelpTool, AddJobTool, AddLeadTool, EditCustomerTool
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.messaging_service import messaging_service
from src.schemas.pwa import ChatMessage, ChatSendRequest, ChatExecuteRequest
from src.models import Message, MessageRole, User, Service, ConversationState, ConversationStatus
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
    service: CRMService = Depends(get_crm_service),
    current_user: User = Depends(get_current_user)
):
    if customer_id == 0:
        # AI Assistant history for this user
        stmt = (
            select(Message)
            .where(
                Message.business_id == service.business_id,
                Message.user_id == current_user.id,
                (Message.from_number == "system") | (Message.to_number == "system")
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

    # 1. Get Customer to find phone number/User ID
    customer = await service.customer_repo.get_by_id(customer_id, service.business_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    phone = customer.phone
    if not phone:
        return []

    # 2. Query messages by phone
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
        # 1. Persist User Message
        user_msg = Message(
            business_id=service.business_id,
            user_id=current_user.id,
            from_number=current_user.phone_number or "pwa_user",
            to_number="system",
            body=request.message,
            role=MessageRole.USER,
            channel_type="pwa_chat"
        )
        service.session.add(user_msg)

        # 2. Parse using LLM
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

        # 1.1 Handle Greetings/Keywords before parser
        lower_msg = request.message.lower().strip()
        msg_template_service = TemplateService()

        tool_call = await parser.parse(
            text=request.message,
            system_time=system_time,
            service_catalog=service_catalog,
            channel_name="pwa_chat",
            user_context=user_context
        )

        response_text = ""
        if tool_call is None or tool_call == "None": 
            if lower_msg in ["hi", "hello", "hey", "greetings"]:
                response_text = msg_template_service.render("welcome_back")
            else:
                # Use templated help message as fallback
                response_text = msg_template_service.render("help_message")
        elif isinstance(tool_call, str):
            response_text = tool_call
        else:
            # 3. Execute tool
            
            if isinstance(tool_call, HelpTool):
                help_service = HelpService(service.session, parser)
                response_text = await help_service.generate_help_response(
                    user_query=request.message,
                    business_id=service.business_id,
                    user_id=current_user.id,
                    channel="pwa_chat"
                )
            else:
                # 3. Handle Tool Proposal instead of immediate execution
                
                # --- Geocoding Injection Start ---
                try:
                    # Check if it's a tool that has location/address fields we want to expand
                    # We need to import these types, assuming they are available or we check via extraction
                    is_job_tool = isinstance(tool_call, AddJobTool)
                    is_lead_tool = isinstance(tool_call, AddLeadTool)
                    is_edit_customer_tool = isinstance(tool_call, EditCustomerTool)
                    
                    location_query = None
                    if is_job_tool and tool_call.location:
                        location_query = tool_call.location
                    elif is_lead_tool:
                        # For lead, it might be street or location field
                        location_query = tool_call.street or tool_call.location
                    elif is_edit_customer_tool and tool_call.location:
                        location_query = tool_call.location

                    if location_query:
                        # Attempt to resolve
                        geocoder = GeocodingService()
                        # Use business settings for default city/country if available in future
                        lat, lon, street, city, country, postcode, full_address = await geocoder.geocode(location_query)
                        
                        if full_address and full_address != location_query:
                            print(f"DEBUG: Expanded location '{location_query}' to '{full_address}'")
                            
                            if is_job_tool:
                                tool_call.location = full_address
                                if city:
                                    tool_call.city = city
                                if country:
                                    tool_call.country = country
                                # We could also add lat/lon if the model supports it, but sticking to address strings for now
                            elif is_lead_tool:
                                if tool_call.street:
                                    tool_call.street = street or tool_call.street
                                tool_call.location = full_address
                                if city:
                                    tool_call.city = city
                                if country:
                                    tool_call.country = country
                            elif is_edit_customer_tool:
                                tool_call.location = full_address
                except Exception as e:
                    print(f"WARNING: Geocoding failed: {e}")
                    # Continue without expansion
                # --- Geocoding Injection End ---

                # Update ConversationState
                stmt = select(ConversationState).where(ConversationState.user_id == current_user.id)
                res = await service.session.execute(stmt)
                state_record = res.scalar_one_or_none()
                
                if not state_record:
                    state_record = ConversationState(user_id=current_user.id, state=ConversationStatus.IDLE)
                    service.session.add(state_record)
                
                state_record.state = ConversationStatus.WAITING_CONFIRM
                state_record.draft_data = {
                    "tool_name": tool_call.__class__.__name__,
                    "arguments": tool_call.dict()
                }
                
                await service.session.commit()
                
                proposal_data = {
                    "status": "proposed",
                    "content": "I've prepared a draft for you. Please confirm below.",
                    "tool": tool_call.__class__.__name__,
                    "data": tool_call.dict()
                }
                
                # Persist the proposal as a system message so it survives reload
                import json
                # Use default=str to handle datetime or other non-serializable types safely
                response_text = json.dumps(proposal_data, default=str)
        
        # 4. Persist AI Response
        ai_msg = Message(
            business_id=service.business_id,
            user_id=current_user.id,
            from_number="system",
            to_number=current_user.phone_number or "pwa_user",
            body=response_text,
            role=MessageRole.ASSISTANT,
            channel_type="pwa_chat"
        )
        service.session.add(ai_msg)
        
        # Commit all (user message, tool changes, ai response)
        await service.session.commit()
        
        return {"status": "sent", "content": response_text, "reply": response_text}

    customer = await service.customer_repo.get_by_id(request.customer_id, service.business_id)
    if not customer:
        print(f"DEBUG: Customer {request.customer_id} not found for business {service.business_id}")
        raise HTTPException(status_code=404, detail=f"Customer {request.customer_id} not found")
    if not customer.phone:
        print(f"DEBUG: Customer {request.customer_id} has no phone")
        raise HTTPException(status_code=404, detail="Customer has no phone number")
        
    # Persist User Message to Customer
    user_msg = Message(
        business_id=service.business_id,
        user_id=current_user.id,
        from_number=current_user.phone_number or "pwa_user",
        to_number=customer.phone,
        body=request.message,
        role=MessageRole.USER,
        channel_type="pwa_chat"
    )
    service.session.add(user_msg)

    # Send via MessagingService
    # This currently sends externally and logs to MessageLog, but we want it in History (Message)
    await messaging_service.send_message(
        recipient_phone=customer.phone,
        content=request.message,
        channel="whatsapp",
        trigger_source="pwa_chat_manual",
        business_id=service.business_id
    )
    
    # Log the outbound message in History too
    # In a more robust system, MessagingService would return the final content if templated, 
    # but here it's manual so content is request.message.
    outbound_msg = Message(
        business_id=service.business_id,
        user_id=current_user.id,
        from_number="system", # Or maybe the user's business number
        to_number=customer.phone,
        body=request.message,
        role=MessageRole.ASSISTANT,
        channel_type="whatsapp"
    )
    service.session.add(outbound_msg)
    await service.session.commit()
    
    return {"status": "sent"}

@router.post("/execute")
async def execute_tool(
    request: ChatExecuteRequest,
    current_user: User = Depends(get_current_user),
    service: CRMService = Depends(get_crm_service)
):
    # 1. Fetch State
    stmt = select(ConversationState).where(ConversationState.user_id == current_user.id)
    res = await service.session.execute(stmt)
    state_record = res.scalar_one_or_none()
    
    if not state_record or state_record.state != ConversationStatus.WAITING_CONFIRM:
        raise HTTPException(status_code=400, detail="No pending tool call to confirm")
    
    draft = state_record.draft_data
    if not draft or draft.get("tool_name") != request.tool_name:
        raise HTTPException(status_code=400, detail="Tool mismatch or no draft data")
        
    # 2. Reconstruct Tool Call
    # We need a map of tool names to classes. We can import them or use src.uimodels
    from src import uimodels
    from src.tools import invoice_tools
    
    model_map = {
        "AddJobTool": uimodels.AddJobTool,
        "AddLeadTool": uimodels.AddLeadTool,
        "EditCustomerTool": uimodels.EditCustomerTool,
        "ScheduleJobTool": uimodels.ScheduleJobTool,
        "AddRequestTool": uimodels.AddRequestTool,
        "SearchTool": uimodels.SearchTool,
        "UpdateSettingsTool": uimodels.UpdateSettingsTool,
        "ConvertRequestTool": uimodels.ConvertRequestTool,
        "HelpTool": uimodels.HelpTool,
        "GetPipelineTool": uimodels.GetPipelineTool,
        "SendInvoiceTool": invoice_tools.SendInvoiceTool,
        "GetBillingStatusTool": uimodels.GetBillingStatusTool,
        "RequestUpgradeTool": uimodels.RequestUpgradeTool,
        "CreateQuoteTool": uimodels.CreateQuoteTool,
        "SendStatusTool": uimodels.SendStatusTool,
        "LocateEmployeeTool": uimodels.LocateEmployeeTool,
        "CheckETATool": uimodels.CheckETATool,
    }
    
    tool_cls = model_map.get(request.tool_name)
    if not tool_cls:
        raise HTTPException(status_code=400, detail=f"Unsupported tool: {request.tool_name}")
        
    tool_call = tool_cls(**request.arguments)
    
    # 3. Execute
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    messages_path = os.path.join(base_dir, "assets", "messages.yaml")
    template_service = TemplateService(yaml_path=messages_path)
    
    executor = ToolExecutor(
        session=service.session,
        business_id=service.business_id,
        user_id=current_user.id,
        user_phone=current_user.phone_number or "",
        template_service=template_service
    )
    
    response_text, _ = await executor.execute(tool_call)
    
    # 4. Persist result as Assistant Message
    # This helps keep history clean and shows the user what happened
    ai_msg = Message(
        business_id=service.business_id,
        user_id=current_user.id,
        from_number="system",
        to_number=current_user.phone_number or "pwa_user",
        body=response_text,
        role=MessageRole.ASSISTANT,
        channel_type="pwa_chat"
    )
    service.session.add(ai_msg)
    
    # 5. Reset State
    state_record.state = ConversationStatus.IDLE
    state_record.draft_data = None
    
    await service.session.commit()
    
    return {"status": "sent", "content": response_text}
