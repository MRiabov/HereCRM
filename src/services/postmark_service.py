import logging
import httpx
from typing import Optional

from src.config import settings


class PostmarkService:
    """Service for sending and receiving Email messages via Postmark."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Postmark configuration
        self.server_token = settings.postmark_server_token
        self.from_email = settings.from_email_address
        self.api_url = "https://api.postmarkapp.com/email"
        
        if not self.server_token or not self.from_email:
            self.logger.warning(
                "Postmark credentials not configured. Email functionality will be disabled."
            )
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> bool:
        """
        Send an email via Postmark.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content (plain text)
            in_reply_to: Optional Message-ID header for threading
            references: Optional References header for threading
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.server_token or not self.from_email:
            self.logger.error("Cannot send email: Postmark not configured")
            return False
        
        try:
            # Prepare email payload
            payload = {
                "From": self.from_email,
                "To": to_email,
                "Subject": subject,
                "TextBody": body,
            }
            
            # Add threading headers if provided
            headers_dict = {}
            if in_reply_to:
                headers_dict["In-Reply-To"] = in_reply_to
            if references:
                headers_dict["References"] = references
            
            if headers_dict:
                payload["Headers"] = [
                    {"Name": key, "Value": value}
                    for key, value in headers_dict.items()
                ]
            
            # Send request to Postmark API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-Postmark-Server-Token": self.server_token
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info(
                        f"Email sent successfully. MessageID: {result.get('MessageID')}"
                    )
                    return True
                else:
                    self.logger.error(
                        f"Postmark API error: {response.status_code} - {response.text}"
                    )
                    return False
                    
        except httpx.TimeoutException:
            self.logger.error(f"Timeout sending email to {to_email}")
            return False
            
        except Exception as e:
            self.logger.exception(f"Unexpected error sending email to {to_email}: {e}")
            return False
