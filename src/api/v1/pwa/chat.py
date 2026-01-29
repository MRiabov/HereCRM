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
from src.schemas.pwa import (
    ChatMessage,
    ChatSendRequest,
    ChatExecuteRequest,
    ChatMessageUpdate,
)
from src.models import (
    Message,
    MessageRole,
    User,
    Service,
    ConversationState,
    ConversationStatus,
    Business,
    MessageTriggerSource,
    MessageType,
)
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()


async def get_crm_service(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CRMService:
    return CRMService(session, business_id=current_user.business_id)


@router.get("/history", response_model=List[ChatMessage])
async def get_assistant_history(
    service: CRMService = Depends(get_crm_service),
    current_user: User = Depends(get_current_user),
):
    """
    Returns AI Assistant history for the current user (where from_number/to_number is 'system').
    """
    stmt = (
        select(Message)
        .where(
            Message.business_id == service.business_id,
            Message.user_id == current_user.id,
            (Message.from_number == "system") | (Message.to_number == "system"),
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
            is_outbound=(msg.role == MessageRole.ASSISTANT),
            is_executed=msg.is_executed,
            id=msg.id,
        )
        for msg in messages
    ]


@router.get("/history/{customer_id}", response_model=List[ChatMessage])
async def get_chat_history(
    customer_id: int,
    service: CRMService = Depends(get_crm_service),
    current_user: User = Depends(get_current_user),
):
    if customer_id == 0:
        # Backward compatibility: forward to get_assistant_history logic
        return await get_assistant_history(service, current_user)

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
            Message.business_id == service.business_id,
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
            is_outbound=(msg.role == MessageRole.ASSISTANT),
            is_executed=msg.is_executed,
            id=msg.id,
        )
        for msg in messages
    ]


@router.post("/send")
async def send_message(
    request: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    service: CRMService = Depends(get_crm_service),
):
    print(
        f"DEBUG: Processing send_message for customer_id={request.customer_id} business_id={service.business_id}"
    )

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
            channel_type=MessageType.PWA_CHAT,
        )
        service.session.add(user_msg)

        # 2. Parse using LLM
        system_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Fetch service catalog for context
        catalog_stmt = select(Service).where(Service.business_id == service.business_id)
        catalog_result = await service.session.execute(catalog_stmt)
        services_list = catalog_result.scalars().all()
        service_catalog = "\n".join(
            [f"- {s.name}: €{s.default_price}" for s in services_list]
        )

        user_context = {
            "role": current_user.role,
            "name": current_user.name,
            "business_id": current_user.business_id,
        }

        # 1.1 Handle Greetings/Keywords before parser
        lower_msg = request.message.lower().strip()
        msg_template_service = TemplateService()

        feedback = None
        tool_call = None
        response_text = ""

        for attempt in range(2):  # Up to 2 attempts
            tool_call = await parser.parse(
                text=request.message,
                system_time=system_time,
                service_catalog=service_catalog,
                channel_name=MessageType.PWA_CHAT.value,
                user_context=user_context,
                feedback=feedback,
            )

            if tool_call is None or tool_call == "None":
                if lower_msg in ["hi", "hello", "hey", "greetings"]:
                    response_text = msg_template_service.render("welcome_back")
                else:
                    # Use templated help message as fallback
                    response_text = msg_template_service.render("help_message")
                break
            elif isinstance(tool_call, str):
                response_text = tool_call
                break
            else:
                # 3. Execute tool

                if isinstance(tool_call, HelpTool):
                    help_service = HelpService(service.session, parser)
                    response_text = await help_service.generate_help_response(
                        user_query=request.message,
                        business_id=service.business_id,
                        user_id=current_user.id,
                        channel=MessageType.PWA_CHAT,
                    )
                    break
                else:
                    # 3. Handle Tool Proposal instead of immediate execution

                    # --- Geocoding Injection Start ---
                    try:
                        # Check if it's a tool that has location/address fields we want to expand
                        is_job_tool = isinstance(tool_call, AddJobTool)
                        is_lead_tool = isinstance(tool_call, AddLeadTool)
                        is_edit_customer_tool = isinstance(tool_call, EditCustomerTool)

                        location_query = None
                        if is_job_tool and tool_call.location:
                            location_query = tool_call.location
                        elif is_lead_tool:
                            location_query = tool_call.street or tool_call.location
                        elif is_edit_customer_tool and tool_call.location:
                            location_query = tool_call.location

                        if location_query:
                            # Resolve defaults
                            business = await service.session.get(
                                Business, current_user.business_id
                            )
                            prefs = current_user.preferences or {}

                            default_city = (
                                business.default_city if business else None
                            ) or prefs.get("default_city")
                            default_country = (
                                business.default_country if business else None
                            ) or prefs.get("default_country")

                            safeguard_enabled = prefs.get(
                                "geocoding_safeguard_enabled", False
                            )
                            if isinstance(safeguard_enabled, str):
                                safeguard_enabled = safeguard_enabled.lower() in [
                                    "true",
                                    "yes",
                                    "on",
                                    "1",
                                ]

                            max_dist = prefs.get("geocoding_max_distance_km", 100.0)
                            try:
                                max_dist = float(max_dist)
                            except (ValueError, TypeError):
                                max_dist = 100.0

                            # Attempt to resolve
                            geocoder = GeocodingService()
                            (
                                lat,
                                lon,
                                street,
                                city,
                                country,
                                postcode,
                                full_address,
                            ) = await geocoder.geocode(
                                location_query,
                                default_city=default_city,
                                default_country=default_country,
                                safeguard_enabled=safeguard_enabled,
                                max_distance_km=max_dist,
                            )

                            if safeguard_enabled and default_city and not lat:
                                if attempt == 0:
                                    feedback = f"The location '{location_query}' is too far from {default_city} or not found. Please try to infer a more accurate address or city."
                                    continue
                                else:
                                    response_text = f"Sorry, the location '{location_query}' seems too far from your default city ({default_city}) or could not be found. Please provide a more specific address or update your default city."
                                    break

                            if full_address and full_address != location_query:
                                if is_job_tool:
                                    tool_call.location = full_address
                                    if city:
                                        tool_call.city = city
                                    if country:
                                        tool_call.country = country
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
                    # --- Geocoding Injection End ---

                    # If we reached here without break/continue, geocoding succeeded
                    # Update ConversationState
                    stmt = select(ConversationState).where(
                        ConversationState.user_id == current_user.id
                    )
                    res = await service.session.execute(stmt)
                    state_record = res.scalar_one_or_none()

                    if not state_record:
                        state_record = ConversationState(
                            user_id=current_user.id, state=ConversationStatus.IDLE
                        )
                        service.session.add(state_record)

                    state_record.state = ConversationStatus.WAITING_CONFIRM
                    state_record.draft_data = {
                        "tool_name": tool_call.__class__.__name__,
                        "arguments": tool_call.dict(),
                    }

                    await service.session.commit()

                    proposal_data = {
                        "status": "proposed",
                        "description": "I've prepared a draft for you. Please confirm below.",
                        "tool": tool_call.__class__.__name__,
                        "data": tool_call.dict(),
                    }

                    import json

                    response_text = json.dumps(proposal_data, default=str)
                    break

        # 4. Persist AI Response
        ai_msg = Message(
            business_id=service.business_id,
            user_id=current_user.id,
            from_number="system",
            to_number=current_user.phone_number or "pwa_user",
            body=response_text,
            role=MessageRole.ASSISTANT,
            channel_type=MessageType.PWA_CHAT,
        )
        service.session.add(ai_msg)

        # Commit all (user message, tool changes, ai response)
        await service.session.commit()

        return {"status": "SENT", "content": response_text, "reply": response_text}

    customer = await service.customer_repo.get_by_id(
        request.customer_id, service.business_id
    )
    if not customer:
        print(
            f"DEBUG: Customer {request.customer_id} not found for business {service.business_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Customer {request.customer_id} not found"
        )
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
        channel_type=MessageType.PWA_CHAT,
    )
    service.session.add(user_msg)

    # Send via MessagingService
    # This currently sends externally and logs to MessageLog, but we want it in History (Message)
    await messaging_service.send_message(
        recipient_phone=customer.phone,
        content=request.message,
        channel=MessageType.WHATSAPP,
        trigger_source=MessageTriggerSource.PWA_CHAT_MANUAL,
        business_id=service.business_id,
    )

    # Log the outbound message in History too
    # In a more robust system, MessagingService would return the final content if templated,
    # but here it's manual so content is request.message.
    outbound_msg = Message(
        business_id=service.business_id,
        user_id=current_user.id,
        from_number="system",  # Or maybe the user's business number
        to_number=customer.phone,
        body=request.message,
        role=MessageRole.ASSISTANT,
        channel_type=MessageType.WHATSAPP,
    )
    service.session.add(outbound_msg)
    await service.session.commit()

    return {"status": "SENT"}


@router.post("/execute")
async def execute_tool(
    request: ChatExecuteRequest,
    current_user: User = Depends(get_current_user),
    service: CRMService = Depends(get_crm_service),
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
        "AutorouteTool": uimodels.AutorouteTool,
    }

    tool_cls = model_map.get(request.tool_name)
    if not tool_cls:
        raise HTTPException(
            status_code=400, detail=f"Unsupported tool: {request.tool_name}"
        )

    from pydantic import ValidationError

    try:
        tool_call = tool_cls(**request.arguments)
    except (ValidationError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 3. Execute
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    messages_path = os.path.join(base_dir, "assets", "messages.yaml")
    template_service = TemplateService(yaml_path=messages_path)

    executor = ToolExecutor(
        session=service.session,
        business_id=service.business_id,
        user_id=current_user.id,
        user_phone=current_user.phone_number or "",
        template_service=template_service,
    )

    response_text, data = await executor.execute(tool_call)

    # 4. Persist result as Assistant Message
    # This helps keep history clean and shows the user what happened
    ai_msg = Message(
        business_id=service.business_id,
        user_id=current_user.id,
        from_number="system",
        to_number=current_user.phone_number or "pwa_user",
        body=response_text,
        role=MessageRole.ASSISTANT,
        channel_type=MessageType.PWA_CHAT,
    )
    service.session.add(ai_msg)

    # 4.1 Mark the draft message as executed
    # We find the most recent ASSISTANT message that contains "proposed" status in its JSON body
    draft_stmt = (
        select(Message)
        .where(
            Message.business_id == service.business_id,
            Message.user_id == current_user.id,
            Message.role == MessageRole.ASSISTANT,
            Message.body.like('%"status": "proposed"%'),
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    draft_res = await service.session.execute(draft_stmt)
    last_draft = draft_res.scalar_one_or_none()
    if last_draft:
        last_draft.is_executed = True

    # 5. Reset State
    state_record.state = ConversationStatus.IDLE
    state_record.draft_data = None

    await service.session.commit()

    return {
        "status": "SENT",
        "content": response_text,
        "tool": request.tool_name,
        "data": data,
        "is_executed": True,
    }


@router.patch("/message/{message_id}")
async def update_message(
    message_id: int,
    update_data: ChatMessageUpdate,
    service: CRMService = Depends(get_crm_service),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Message).where(
        Message.id == message_id, Message.business_id == service.business_id
    )
    result = await service.session.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.user_id != current_user.id:
        # Only allow users to edit their own messages
        raise HTTPException(
            status_code=403, detail="You can only edit your own messages"
        )

    message.body = update_data.message
    await service.session.commit()

    return {"status": "updated", "id": message.id, "content": message.body}
