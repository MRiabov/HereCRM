from typing import Optional, Tuple
import json
import asyncio
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.models import User
from sqlalchemy import select

class GoogleCalendarService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        
        # Check if Google credentials are configured
        self.is_configured = all([
            settings.google_client_id,
            settings.google_client_secret,
            settings.google_redirect_uri
        ])
        
        if self.is_configured:
            self.client_config = {
                "web": {
                    "client_id": settings.google_client_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": settings.google_client_secret,
                    "redirect_uris": [settings.google_redirect_uri]
                }
            }
        else:
            self.client_config = {}

    def get_auth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        if not self.is_configured:
            raise ValueError("Google Calendar API is not configured. Missing client_id, client_secret, or redirect_uri.")
            
        flow = Flow.from_client_config(
            client_config=self.client_config,
            scopes=self.scopes,
            redirect_uri=settings.google_redirect_uri
        )
        # prompt='consent' and access_type='offline' are needed to get a refresh_token
        auth_url, state = flow.authorization_url(
            prompt='consent', 
            state=state, 
            access_type='offline',
            include_granted_scopes='true'
        )
        return auth_url, state

    async def process_auth_callback(self, code: str, user_id: int, db: AsyncSession) -> bool:
        if not self.is_configured:
            raise ValueError("Google Calendar API is not configured.")
            
        flow = Flow.from_client_config(
            client_config=self.client_config,
            scopes=self.scopes,
            redirect_uri=settings.google_redirect_uri
        )
        
        # flow.fetch_token is blocking, run in executor
        await asyncio.to_thread(flow.fetch_token, code=code)
        creds = flow.credentials
        
        # Serialize credentials to JSON
        creds_json = json.loads(creds.to_json())
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.google_calendar_credentials = creds_json
            user.google_calendar_sync_enabled = True
            # Caller is responsible for committing the session
            return True
        return False

    def get_credentials_for_user(self, user: User) -> Optional[Credentials]:
        if not user.google_calendar_credentials:
            return None
        
        return Credentials.from_authorized_user_info(
            user.google_calendar_credentials,
            self.scopes
        )
