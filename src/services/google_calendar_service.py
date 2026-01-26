from typing import Optional, Tuple, Any, Dict
import json
import asyncio
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.models import User, Job
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

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
        
        # Also try to get user email if scope allows
        email = None
        try:
            service = build('oauth2', 'v2', credentials=creds)
            user_info = await asyncio.to_thread(service.userinfo().get().execute)
            email = user_info.get("email")
        except Exception as e:
            logger.warning(f"Could not fetch user email during Google Auth: {e}")
        
        if email:
            creds_json["email"] = email

        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.google_calendar_credentials = creds_json
            user.google_calendar_sync_enabled = True
            await db.flush()
            return True
        return False

    async def _get_credentials(self, user: User, db: AsyncSession) -> Optional[Credentials]:
        if not user.google_calendar_credentials:
            return None
        
        creds = Credentials.from_authorized_user_info(
            user.google_calendar_credentials,
            self.scopes
        )
        
        if creds.expired and creds.refresh_token:
            try:
                # creds.refresh is blocking
                await asyncio.to_thread(creds.refresh, Request())
                # Update DB with new credentials
                user.google_calendar_credentials = json.loads(creds.to_json())
                await db.flush()
                logger.info(f"Refreshed Google credentials for user {user.id}")
            except Exception as e:
                logger.error(f"Failed to refresh Google credentials for user {user.id}: {e}")
                return None
                
        return creds

    async def _get_calendar_service(self, user: User, db: AsyncSession):
        creds = await self._get_credentials(user, db)
        if not creds:
            return None
        # build is blocking? Usually yes, but discovery is often cached.
        # Still, we'll run it in thread to be safe.
        return await asyncio.to_thread(build, 'calendar', 'v3', credentials=creds)

    async def _build_event_body(self, job: Job, db: AsyncSession) -> Dict[str, Any]:
        # Ensure customer is loaded
        from sqlalchemy.orm import selectinload
        if not job.customer:
             # Refresh job with customer loaded
             query = select(Job).where(Job.id == job.id).options(selectinload(Job.customer))
             result = await db.execute(query)
             job = result.scalar_one()

        customer_name = job.customer.name if job.customer else "Unknown Customer"
        
        start_time = job.scheduled_at or datetime.now()
        # Default duration 1 hour
        end_time = start_time + timedelta(hours=1)
        
        return {
            'summary': f'Job: {customer_name}',
            'location': job.location or '',
            'description': job.description or '',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'extendedProperties': {
                'shared': {
                    'herecrm_job_id': str(job.id)
                }
            }
        }

    async def create_event(self, job: Job, user: User, db: AsyncSession) -> Optional[str]:
        if not user.google_calendar_sync_enabled:
            return None
            
        service = await self._get_calendar_service(user, db)
        if not service:
            return None
            
        event_body = await self._build_event_body(job, db)
        try:
            # service.events().insert().execute() is blocking
            event = await asyncio.to_thread(
                service.events().insert(calendarId='primary', body=event_body).execute
            )
            logger.info(f"Created GCal event {event['id']} for job {job.id}")
            return event['id']
        except Exception as e:
            logger.error(f"Failed to create GCal event for job {job.id}: {e}")
            return None

    async def update_event(self, job: Job, user: User, db: AsyncSession) -> bool:
        if not user.google_calendar_sync_enabled or not job.gcal_event_id:
            return False
            
        service = await self._get_calendar_service(user, db)
        if not service:
            return False
            
        event_body = await self._build_event_body(job, db)
        try:
            await asyncio.to_thread(
                service.events().update(
                    calendarId='primary', 
                    eventId=job.gcal_event_id, 
                    body=event_body
                ).execute
            )
            logger.info(f"Updated GCal event {job.gcal_event_id} for job {job.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update GCal event {job.gcal_event_id}: {e}")
            return False

    async def delete_event(self, gcal_event_id: str, user: User, db: AsyncSession) -> bool:
        if not user.google_calendar_sync_enabled or not gcal_event_id:
            return False
            
        service = await self._get_calendar_service(user, db)
        if not service:
            return False
            
        try:
            await asyncio.to_thread(
                service.events().delete(calendarId='primary', eventId=gcal_event_id).execute
            )
            logger.info(f"Deleted GCal event {gcal_event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete GCal event {gcal_event_id}: {e}")
            return False
