import abc
import re
import logging

class SMSMessagingService(abc.ABC):
    """Abstract base class for SMS messaging services."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate_e164(self, phone: str) -> bool:
        """Validate phone number is in E.164 format."""
        if not phone:
            return False
        return bool(re.match(r'^\+[1-9]\d{1,14}$', phone))

    @abc.abstractmethod
    async def send_sms(self, to_number: str, body: str) -> bool:
        """
        Send an SMS message.
        
        Args:
            to_number: Recipient phone number in E.164 format
            body: Message content
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        pass
