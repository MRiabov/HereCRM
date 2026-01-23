import httpx
import base64
from src.config import settings
from src.services.channels.base import SMSMessagingService

class TextGridService(SMSMessagingService):
    """Service for sending SMS messages via TextGrid."""

    def __init__(self):
        super().__init__()
        self.account_sid = settings.textgrid_account_sid
        self.auth_token = settings.textgrid_auth_token
        self.from_number = settings.textgrid_phone_number
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            self.logger.warning(
                "TextGrid credentials not fully configured. SMS functionality may be limited."
            )

    async def _send_provider_sms(self, to_number: str, body: str) -> bool:
        """
        Send an SMS message via TextGrid API.
        
        Args:
            to_number: Recipient phone number in E.164 format
            body: Message content
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not all([self.account_sid, self.auth_token, self.from_number]):
            self.logger.error("Cannot send SMS: TextGrid not fully configured")
            return False

        if not self.validate_e164(to_number):
            self.logger.error(f"Invalid recipient phone number: {to_number}")
            return False

        if not body:
            self.logger.error("SMS body cannot be empty")
            return False

        # TextGrid API endpoint (standard assumption for this WP)
        url = "https://api.textgrid.com/v1/sms/send"
        
        auth_str = f"{self.account_sid}:{self.auth_token}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from": self.from_number,
            "to": to_number,
            "text": body
        }

        async with httpx.AsyncClient() as client:
            try:
                # Note: We use a longer timeout for reliability
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                
                if response.status_code in (200, 201, 202):
                    self.logger.info(f"SMS sent successfully via TextGrid to {to_number}")
                    return True
                else:
                    self.logger.error(
                        f"TextGrid API error: {response.status_code} - {response.text}"
                    )
                    return False
                    
            except Exception as e:
                self.logger.exception(f"Unexpected error sending SMS via TextGrid to {to_number}: {e}")
                return False
