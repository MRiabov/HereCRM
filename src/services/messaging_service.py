import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone
import httpx

from src.models import MessageLog, MessageType, MessageStatus, MessageTriggerSource
from src.events import event_bus
from src.database import AsyncSessionLocal
from src.repositories import CustomerRepository
from src.config import settings

logger = logging.getLogger(__name__)


class MessagingService:
    """
    Service responsible for consuming events and sending messages via WhatsApp/SMS.
    Uses an async queue for buffering messages and processes them asynchronously.
    """

    def __init__(self, session_factory=None):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self.session_factory = session_factory or AsyncSessionLocal

    async def send_message(
        self,
        recipient_phone: str,
        content: str,
        channel: MessageType = MessageType.WHATSAPP,
        trigger_source: MessageTriggerSource = MessageTriggerSource.MANUAL,
        business_id: Optional[int] = None,
        log_metadata: Optional[dict] = None,
    ) -> MessageLog:
        """
        Send a message to a recipient via the specified channel.
        """
        # Determine message type
        if isinstance(channel, MessageType):
            message_type = channel
        elif isinstance(channel, str):
            channel_upper = channel.upper()
            if channel_upper == "WHATSAPP":
                message_type = MessageType.WHATSAPP
            elif channel_upper == "SMS":
                message_type = MessageType.SMS
            elif channel_upper == "EMAIL":
                message_type = MessageType.EMAIL
            else:
                message_type = MessageType.WHATSAPP  # Default
        else:
            message_type = MessageType.WHATSAPP

        # Mandatory GSM-7 normalization for SMS to avoid high costs (UCS-2)
        if message_type == MessageType.SMS:
            from src.services.channels.sms_utils import normalize_to_gsm7

            content = normalize_to_gsm7(content)

        # Use a single session for the entire message sending process to avoid detachment issues
        async with self.session_factory() as db:
            if hasattr(db, "sync_session"):
                db.sync_session.expire_on_commit = False
            # 1. Create MessageLog entry with PENDING status
            message_log = MessageLog(
                business_id=business_id,
                recipient_phone=recipient_phone,
                content=content,
                message_type=message_type,
                status=MessageStatus.PENDING,
                trigger_source=trigger_source,
                log_metadata=log_metadata,
            )
            try:
                db.add(message_log)
                await db.commit()
            except Exception as e:
                logger.error(
                    f"Failed to create initial MessageLog (session id: {id(db)}): {e}"
                )
                raise
            # await db.refresh(message_log) - Removed to avoid "Could not refresh instance" error

            # 2. Process sending
            try:
                success = False
                external_id = None

                if message_type == MessageType.WHATSAPP:
                    success, external_id = await self._send_whatsapp(
                        recipient_phone, content
                    )
                elif message_type == MessageType.SMS:
                    success, external_id = await self._send_sms(
                        recipient_phone, content
                    )

                # 3. Update status and track usage
                if success:
                    message_log.status = MessageStatus.SENT
                    message_log.sent_at = datetime.now(timezone.utc)
                    if external_id:
                        message_log.external_id = external_id

                    # Track usage if business_id is known
                    if business_id:
                        from src.services.billing_service import BillingService
                        from src.services.channels.sms_utils import (
                            get_sms_segment_count,
                        )

                        quantity = 1
                        if message_type == MessageType.SMS:
                            quantity = get_sms_segment_count(content)

                        billing_service = BillingService(db)
                        await billing_service.track_message_sent(
                            business_id, quantity=quantity
                        )

                    logger.info(
                        f"Message {message_log.id} sent successfully via {message_type.value}"
                    )
                else:
                    message_log.status = MessageStatus.FAILED
                    message_log.error_message = "Provider request failed"

                await db.commit()

            except Exception as e:
                logger.error(f"Failed to send message {message_log.id}: {e}")
                # Try to log failure in the same session
                try:
                    message_log.status = MessageStatus.FAILED
                    message_log.error_message = str(e)
                    await db.commit()
                except Exception as db_err:
                    logger.error(f"Could not even log failure to DB: {db_err}")
                    await db.rollback()

        return message_log

    async def _send_whatsapp(
        self, recipient_phone: str, content: str
    ) -> tuple[bool, Optional[str]]:
        """
        Send WhatsApp message via Meta Graph API.
        Returns: (success, message_id)
        """
        if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
            logger.warning(
                "WhatsApp settings not configured. Falling back to MOCK log."
            )
            logger.info(f"[MOCK] WhatsApp to {recipient_phone}: {content}")
            return True, f"mock_wa_{int(datetime.now().timestamp())}"

        url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

        # Basic text message payload
        payload = {
            "messaging_product": "WHATSAPP",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": content},
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=10.0
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    # Extract message ID from response: {'messaging_product': 'WHATSAPP', 'contacts': [...], 'messages': [{'id': '...'}]}
                    msg_id = None
                    if "messages" in data and len(data["messages"]) > 0:
                        msg_id = data["messages"][0].get("id")
                    return True, msg_id
                else:
                    logger.error(
                        f"Meta API Error: {response.status_code} - {response.text}"
                    )
                    return False, None
            except Exception as e:
                logger.error(f"Exception sending to Meta API: {e}")
                return False, None

    async def _send_sms(
        self, recipient_phone: str, content: str
    ) -> tuple[bool, Optional[str]]:
        """
        Send SMS via configured SMS provider.
        """
        from src.services.sms_factory import get_sms_service

        try:
            service = get_sms_service()
            success = await service.send_sms(recipient_phone, content)

            # Identify provider for external ID tagging
            provider_name = service.__class__.__name__.lower().replace("service", "")
            return (
                success,
                f"{provider_name}_{int(datetime.now().timestamp())}"
                if success
                else None,
            )
        except Exception as e:
            logger.error(f"Error calling SMS service: {e}")
            return False, None

    async def enqueue_message(
        self,
        recipient_phone: str,
        content: str,
        channel: MessageType = MessageType.WHATSAPP,
        trigger_source: MessageTriggerSource = MessageTriggerSource.EVENT,
        business_id: Optional[int] = None,
        log_metadata: Optional[dict] = None,
    ):
        """
        Add a message to the queue for async processing.

        Args:
            recipient_phone: Phone number of the recipient
            content: Message content to send
            channel: Channel to use (MessageType.WHATSAPP or MessageType.SMS)
            trigger_source: Source that triggered this message
            business_id: ID of the business for billing
            log_metadata: Additional metadata for the message log
        """
        await self._queue.put(
            {
                "recipient_phone": recipient_phone,
                "content": content,
                "channel": channel,
                "trigger_source": trigger_source,
                "business_id": business_id,
                "log_metadata": log_metadata,
            }
        )
        logger.debug(f"Enqueued message for {recipient_phone}")

    async def process_queue(self):
        """
        Background worker that processes messages from the queue.
        Runs indefinitely until stopped.
        """
        logger.info("MessagingService queue processor started")
        self._running = True

        while self._running:
            try:
                # Wait for message with timeout to allow checking _running flag
                message_data = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Check for sentinel value (None) used for stopping
                if message_data is None:
                    self._queue.task_done()
                    break

                # Process the message
                await self.send_message(**message_data)

                # Mark task as done
                self._queue.task_done()

            except asyncio.TimeoutError:
                # No message in queue, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing message from queue: {e}")
                # Continue processing other messages

        logger.info("MessagingService queue processor stopped")

    async def start(self):
        """Start the background queue processor."""
        if not self._running:
            self._worker_task = asyncio.create_task(self.process_queue())
            logger.info("MessagingService started")

    async def stop(self):
        """Stop the background queue processor."""
        if not self._running:
            return

        self._running = False
        # Put sentinel to wake up the getter if it's waiting
        await self._queue.put(None)
        if self._worker_task:
            await self._worker_task
            logger.info("MessagingService stopped")

    async def _get_session_maker(self):
        from src.database import current_db_name

        db_name = current_db_name.get()
        if db_name:
            from src.database import engine_registry

            return await engine_registry.get_session_maker(db_name)
        return self.session_factory

    # Event Handlers

    async def handle_job_created(self, data: dict):
        """
        Handle JOB_CREATED event.
        """
        job_id = data.get("job_id")
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")

        if job_id is None or customer_id is None or business_id is None:
            logger.error(f"Missing data in JOB_CREATED event: {data}")
            return

        logger.info(f"Handling JOB_CREATED for job {job_id}")

        session_maker = await self._get_session_maker()
        async with session_maker() as db:
            customer_repo = CustomerRepository(db)
            customer = await customer_repo.get_by_id(customer_id, business_id)

            if not customer or not customer.phone:
                logger.warning(
                    f"Could not find phone number for customer {customer_id}"
                )
                return

            content = f"Your job has been booked! Job ID: {job_id}"

            await self.enqueue_message(
                recipient_phone=customer.phone,
                content=content,
                trigger_source=MessageTriggerSource.JOB_BOOKED,
                business_id=business_id,
            )

    async def handle_job_scheduled(self, data: dict):
        """
        Handle JOB_SCHEDULED event.
        """
        job_id = data.get("job_id")
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")
        scheduled_at_str = data.get("scheduled_at")

        if job_id is None or customer_id is None or business_id is None:
            logger.error(f"Missing data in JOB_SCHEDULED event: {data}")
            return

        logger.info(f"Handling JOB_SCHEDULED for job {job_id}")

        session_maker = await self._get_session_maker()
        async with session_maker() as db:
            customer_repo = CustomerRepository(db)
            customer = await customer_repo.get_by_id(customer_id, business_id)

            if not customer or not customer.phone:
                logger.warning(
                    f"Could not find phone number for customer {customer_id}"
                )
                return

            content = f"Your job has been scheduled for {scheduled_at_str}"

            await self.enqueue_message(
                recipient_phone=customer.phone,
                content=content,
                trigger_source=MessageTriggerSource.JOB_SCHEDULED,
                business_id=business_id,
            )

    async def handle_on_my_way(self, data: dict):
        """
        Handle ON_MY_WAY event.
        """
        customer_id = data.get("customer_id")
        business_id = data.get("business_id")
        eta_minutes = data.get("eta_minutes")

        if customer_id is None or business_id is None:
            logger.error(f"Missing data in ON_MY_WAY event: {data}")
            return

        logger.info(f"Handling ON_MY_WAY for customer {customer_id}")

        session_maker = await self._get_session_maker()
        async with session_maker() as db:
            customer_repo = CustomerRepository(db)
            customer = await customer_repo.get_by_id(customer_id, business_id)

            if not customer or not customer.phone:
                logger.warning(
                    f"Could not find phone number for customer {customer_id}"
                )
                return

            eta_text = f" ETA: {eta_minutes} minutes" if eta_minutes else ""
            content = f"We're on our way!{eta_text}"

            await self.enqueue_message(
                recipient_phone=customer.phone,
                content=content,
                trigger_source=MessageTriggerSource.ON_MY_WAY,
                business_id=business_id,
            )

    async def handle_send_status_message(self, data: dict):
        """
        Handle SEND_STATUS_MESSAGE event from ToolExecutor.
        """
        print(f"DEBUG: handle_send_status_message received data: {data}")
        business_id = data.get("business_id")
        raw_status = data.get("status_type", "unknown")
        status_type = str(
            raw_status.value if hasattr(raw_status, "value") else raw_status
        )
        message_content = data.get("message_content")
        recipient_phone = data.get("customer_phone")

        if not business_id or not recipient_phone:
            logger.error(
                f"Missing business_id or recipient_phone in SEND_STATUS_MESSAGE: {data}"
            )
            return

        print(f"DEBUG: Proceeding to enqueue message for {recipient_phone}")
        # Determine content
        if message_content:
            content = message_content
        else:
            # Default templates
            templates = {
                "on_way": "We're on our way! See you soon.",
                "running_late": "We're running a bit late, but we'll be there as soon as possible.",
                "start_job": "We've started the job. We'll let you know when we're finished.",
                "finish_job": "The job is complete! Thank you for choosing us.",
            }
            content = templates.get(status_type, f"Update on your job: {status_type}")

        await self.enqueue_message(
            recipient_phone=recipient_phone,
            content=content,
            trigger_source=MessageTriggerSource.STATUS_CHANGE,
            business_id=business_id,
            log_metadata={"status_type": status_type},
        )

    def register_handlers(self):
        """
        Register this service's event handlers with the EventBus.
        Should be called during application startup.
        """
        event_bus.subscribe("JOB_CREATED", self.handle_job_created)
        event_bus.subscribe("JOB_SCHEDULED", self.handle_job_scheduled)
        event_bus.subscribe("ON_MY_WAY", self.handle_on_my_way)
        event_bus.subscribe("SEND_STATUS_MESSAGE", self.handle_send_status_message)
        logger.info("MessagingService handlers registered with EventBus")


# Global singleton instance
messaging_service = MessagingService()
