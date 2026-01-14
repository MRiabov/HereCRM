import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

from src.models import MessageLog, MessageType, MessageStatus
from src.events import JobBookedEvent, JobScheduledEvent, OnMyWayEvent
from src.services.event_bus import event_bus
from src.database import get_db

logger = logging.getLogger(__name__)


class MessagingService:
    """
    Service responsible for consuming events and sending messages via WhatsApp/SMS.
    Uses an async queue for buffering messages and processes them asynchronously.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def send_message(
        self,
        recipient_phone: str,
        content: str,
        channel: str = "whatsapp",
        trigger_source: str = "manual",
    ) -> MessageLog:
        """
        Send a message to a recipient via the specified channel.
        
        Args:
            recipient_phone: Phone number of the recipient
            content: Message content to send
            channel: Channel to use ("whatsapp" or "sms")
            trigger_source: Source that triggered this message
            
        Returns:
            MessageLog: The created message log entry
        """
        # Determine message type
        message_type = MessageType.WHATSAPP if channel == "whatsapp" else MessageType.SMS
        
        # Create MessageLog entry with PENDING status
        async for db in get_db():
            message_log = MessageLog(
                recipient_phone=recipient_phone,
                content=content,
                message_type=message_type,
                status=MessageStatus.PENDING,
                trigger_source=trigger_source,
            )
            db.add(message_log)
            await db.commit()
            await db.refresh(message_log)
            
            try:
                # Mock sending message (in production, this would call external API)
                logger.info(
                    f"[MOCK] Sending {channel} message to {recipient_phone}: {content[:50]}..."
                )
                
                # Simulate API call delay
                await asyncio.sleep(0.1)
                
                # Update status to SENT
                message_log.status = MessageStatus.SENT
                message_log.sent_at = datetime.now(timezone.utc)
                message_log.external_id = f"mock_{message_log.id}_{int(datetime.now(timezone.utc).timestamp())}"
                
                await db.commit()
                await db.refresh(message_log)
                
                logger.info(f"Message {message_log.id} sent successfully")
                
            except Exception as e:
                # Update status to FAILED on error
                logger.error(f"Failed to send message {message_log.id}: {e}")
                message_log.status = MessageStatus.FAILED
                message_log.error_message = str(e)
                await db.commit()
                await db.refresh(message_log)
            
            return message_log

    async def enqueue_message(
        self,
        recipient_phone: str,
        content: str,
        channel: str = "whatsapp",
        trigger_source: str = "event",
    ):
        """
        Add a message to the queue for async processing.
        
        Args:
            recipient_phone: Phone number of the recipient
            content: Message content to send
            channel: Channel to use ("whatsapp" or "sms")
            trigger_source: Source that triggered this message
        """
        await self._queue.put({
            "recipient_phone": recipient_phone,
            "content": content,
            "channel": channel,
            "trigger_source": trigger_source,
        })
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
                message_data = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                
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
        self._running = False
        if self._worker_task:
            await self._worker_task
            logger.info("MessagingService stopped")

    # Event Handlers

    async def handle_job_booked(self, event: JobBookedEvent):
        """
        Handle JobBookedEvent by sending a confirmation message to the customer.
        
        Args:
            event: The JobBookedEvent containing job details
        """
        logger.info(f"Handling JobBookedEvent for job {event.job_id}")
        
        # TODO: Fetch customer phone number from database
        # For now, we'll enqueue a placeholder message
        content = f"Your job has been booked! Job ID: {event.job_id}"
        
        # Enqueue message for async processing
        await self.enqueue_message(
            recipient_phone="placeholder",  # TODO: Get from customer
            content=content,
            trigger_source="job_booked",
        )

    async def handle_job_scheduled(self, event: JobScheduledEvent):
        """
        Handle JobScheduledEvent by sending a scheduling confirmation to the customer.
        
        Args:
            event: The JobScheduledEvent containing scheduling details
        """
        logger.info(f"Handling JobScheduledEvent for job {event.job_id}")
        
        # TODO: Fetch customer phone number from database
        content = f"Your job has been scheduled for {event.scheduled_at.strftime('%Y-%m-%d %H:%M')}"
        
        # Enqueue message for async processing
        await self.enqueue_message(
            recipient_phone="placeholder",  # TODO: Get from customer
            content=content,
            trigger_source="job_scheduled",
        )

    async def handle_on_my_way(self, event: OnMyWayEvent):
        """
        Handle OnMyWayEvent by notifying the customer that the technician is en route.
        
        Args:
            event: The OnMyWayEvent containing ETA details
        """
        logger.info(f"Handling OnMyWayEvent for customer {event.customer_id}")
        
        # TODO: Fetch customer phone number from database
        eta_text = f" ETA: {event.eta_minutes} minutes" if event.eta_minutes else ""
        content = f"We're on our way!{eta_text}"
        
        # Enqueue message for async processing
        await self.enqueue_message(
            recipient_phone="placeholder",  # TODO: Get from customer
            content=content,
            trigger_source="on_my_way",
        )

    def register_handlers(self):
        """
        Register this service's event handlers with the EventBus.
        Should be called during application startup.
        """
        event_bus.subscribe(JobBookedEvent, self.handle_job_booked)
        event_bus.subscribe(JobScheduledEvent, self.handle_job_scheduled)
        event_bus.subscribe(OnMyWayEvent, self.handle_on_my_way)
        logger.info("MessagingService handlers registered with EventBus")


# Global singleton instance
messaging_service = MessagingService()
