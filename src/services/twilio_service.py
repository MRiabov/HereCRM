from twilio.rest import Client
import logging
from src.config import settings

logger = logging.getLogger(__name__)

class TwilioService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TwilioService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        else:
            logger.warning("Twilio credentials not found via settings.")
            self.client = None
        
        self.from_number = settings.twilio_phone_number

    def send_sms(self, to_number: str, body: str) -> str:
        """
        Sends an SMS message using Twilio.
        
        Args:
            to_number: The destination phone number (E.164 format).
            body: The text of the message to send.
            
        Returns:
            str: The Twilio Message SID.
            
        Raises:
            Exception: If Twilio client is not initialized or sending fails.
        """
        if not self.client:
            raise Exception("Twilio client is not initialized. Check configuration.")
            
        if not self.from_number:
            raise Exception("Twilio phone number is not configured.")

        try:
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_number
            )
            logger.info(f"Sent SMS to {to_number}, SID: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            raise
