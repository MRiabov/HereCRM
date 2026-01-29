import abc
import re
import logging
from src.services.channels.sms_utils import normalize_to_gsm7


class SMSMessagingService(abc.ABC):
    """Abstract base class for SMS messaging services."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate_e164(self, phone: str) -> bool:
        """Validate phone number is in E.164 format."""
        if not phone:
            return False
        return bool(re.match(r"^\+[1-9]\d{1,14}$", phone))

    async def send_sms(self, to_number: str, body: str) -> bool:
        """
        Send an SMS message.
        Automatically normalizes the body to GSM-7 characters to minimize costs.

        Args:
            to_number: Recipient phone number in E.164 format
            body: Message content

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        normalized_body = normalize_to_gsm7(body)

        if normalized_body != body:
            self.logger.info(
                f"Normalized SMS body to GSM-7 (Original length: {len(body)}, New: {len(normalized_body)})"
            )

        return await self._send_provider_sms(to_number, normalized_body)

    @abc.abstractmethod
    async def _send_provider_sms(self, to_number: str, body: str) -> bool:
        """
        Provider-specific implementation of sending SMS.
        The body is guaranteed to be GSM-7 normalized.

        Args:
            to_number: Recipient phone number in E.164 format
            body: Message content (GSM-7 normalized)

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        pass
