from sqlalchemy.ext.asyncio import AsyncSession
from src.services.accounting.quickbooks_auth import QuickBooksAuthService
from src.services.template_service import TemplateService
import logging
from datetime import datetime, timezone


class AccountingToolsHandler:
    def __init__(
        self, session: AsyncSession, business_id: int, template_service: TemplateService
    ):
        self.session = session
        self.business_id = business_id
        self.template_service = template_service
        self.auth_service = QuickBooksAuthService(session)
        self.logger = logging.getLogger(__name__)

    async def connect_quickbooks(self) -> str:
        # Generate URL
        # We need a proper way to expose the URL.
        # Ideally, we format it nicely.
        auth_url = self.auth_service.generate_auth_url(self.business_id)
        return self.template_service.render("qb_connect_link", url=auth_url)

    async def disconnect_quickbooks(self) -> str:
        await self.auth_service.disconnect(self.business_id)
        return self.template_service.render("qb_disconnected")

    async def get_sync_status(self) -> str:
        # Query credentials exist?
        creds = await self.auth_service.get_credentials(self.business_id)
        if not creds:
            return self.template_service.render("qb_not_connected")

        # Check expiry
        expiry = creds.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        status = "✅ Connected"
        if expiry < datetime.now(timezone.utc):
            status = "⚠️ Connected (Token Expired - attempting refresh on next sync)"

        return self.template_service.render(
            "qb_status", status=status, realm_id=creds.realm_id
        )
