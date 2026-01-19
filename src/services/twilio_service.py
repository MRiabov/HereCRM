import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from src.config import settings


class TwilioService:
    """Service for sending and receiving SMS messages via Twilio."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Twilio client if credentials are available
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
            self.from_number = settings.twilio_phone_number
        else:
            self.client = None
            self.from_number = None
            self.logger.warning(
                "Twilio credentials not configured. SMS functionality will be disabled."
            )
    
    async def send_sms(self, to_number: str, body: str) -> bool:
        """
        Send an SMS message via Twilio.
        
        Args:
            to_number: Recipient phone number in E.164 format (e.g., +1234567890)
            body: Message content
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not self.client or not self.from_number:
            self.logger.error("Cannot send SMS: Twilio not configured")
            return False
        
        try:
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_number
            )
            
            self.logger.info(
                f"SMS sent successfully. SID: {message.sid}, Status: {message.status}"
            )
            return True
            
        except TwilioRestException as e:
            self.logger.error(
                f"Twilio API error sending SMS to {to_number}: {e.msg} (Code: {e.code})"
            )
            return False
            
        except Exception as e:
            self.logger.exception(f"Unexpected error sending SMS to {to_number}: {e}")
            return False
