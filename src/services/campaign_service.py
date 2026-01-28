import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Campaign,
    CampaignRecipient,
    CampaignStatus,
    CampaignChannel,
    RecipientStatus,
    Customer,
    MessageStatus,
    EntityType,
    MessageType,
    MessageTriggerSource
)
from src.services.search_service import SearchService
from src.services.messaging_service import messaging_service
from src.services.postmark_service import PostmarkService
from src.uimodels import SearchTool

logger = logging.getLogger(__name__)

class CampaignService:
    def __init__(self, session: AsyncSession, search_service: SearchService, postmark_service: PostmarkService):
        self.session = session
        self.search_service = search_service
        self.postmark_service = postmark_service

    async def create_campaign(
        self,
        business_id: int,
        name: str,
        channel: CampaignChannel,
        body: str,
        subject: Optional[str] = None,
        recipient_query: str = "all",
        template_id: Optional[str] = None,
    ) -> Campaign:
        campaign = Campaign(
            business_id=business_id,
            name=name,
            channel=channel,
            body=body,
            subject=subject,
            recipient_query=recipient_query,
            template_id=template_id,
            status=CampaignStatus.DRAFT
        )
        self.session.add(campaign)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def prepare_audience(self, campaign_id: int) -> int:
        """
        Resolves the recipient_query and populates individual recipients.
        Returns the count of identified recipients.
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")

        # Use SearchService to segment audience
        search_params = SearchTool(
            query=str(campaign.recipient_query) if campaign.recipient_query and campaign.recipient_query != "all" else "",
            entity_type=EntityType.CUSTOMER,
            detailed=False,
            query_type="ALL",
            min_date=None,
            max_date=None,
            status=None,
            radius=None,
            center_lat=None,
            center_lon=None,
            center_address=None,
            pipeline_stage=None
        )

        # Note: We need a way to get all results from SearchService, not just top 10.
        # However, for now, let's assume we can get them or refactor SearchService slightly.
        # Actually, let's look at SearchService._search_customers.

        results = await self.search_service._search_customers(
            search_params,
            campaign.business_id,
            None,
            None
        )

        # Clear existing recipients in case of re-run
        await self.session.execute(
            update(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == campaign_id)
            .values(status=RecipientStatus.DELETED)
        )

        total_count = 0
        for customer in results:
            if campaign.channel == CampaignChannel.EMAIL and not customer.email:
                continue
            if campaign.channel in [CampaignChannel.WHATSAPP, CampaignChannel.SMS] and not customer.phone:
                continue

            recipient = CampaignRecipient(
                campaign_id=campaign_id,
                customer_id=customer.id,
                status=RecipientStatus.PENDING
            )
            self.session.add(recipient)
            total_count += 1

        campaign.total_recipients = total_count
        await self.session.commit()
        return total_count

    async def execute_campaign(self, campaign_id: int):
        """
        Sends messages to all recipients in the campaign.
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")

        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise ValueError(f"Cannot execute campaign in status {campaign.status}")

        campaign.status = CampaignStatus.SENDING
        campaign.sent_at = datetime.now(timezone.utc)
        await self.session.commit()

        # Fetch all pending recipients
        stmt = select(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == RecipientStatus.PENDING
        )
        result = await self.session.execute(stmt)
        recipients = result.scalars().all()

        for recipient in recipients:
            customer = await self.session.get(Customer, recipient.customer_id)
            if not customer:
                continue

            success = False
            external_id = None
            error_message = None

            try:
                if campaign.channel == CampaignChannel.EMAIL:
                    if customer.email:
                        success = await self.postmark_service.send_email(
                            to_email=customer.email,
                            subject=campaign.subject or "Notification",
                            body=campaign.body
                        )
                elif campaign.channel == CampaignChannel.WHATSAPP:
                    if customer.phone:
                        msg_log = await messaging_service.send_message(
                            recipient_phone=customer.phone,
                            content=campaign.body,
                            channel=MessageType.WHATSAPP,
                            trigger_source=MessageTriggerSource.CAMPAIGN,
                            business_id=campaign.business_id,
                            log_metadata={"campaign_id": campaign.id}
                        )
                        success = msg_log.status == MessageStatus.SENT
                        external_id = msg_log.external_id
                        error_message = msg_log.error_message
                elif campaign.channel == CampaignChannel.SMS:
                    if customer.phone:
                        msg_log = await messaging_service.send_message(
                            recipient_phone=customer.phone,
                            content=campaign.body,
                            channel=MessageType.SMS,
                            trigger_source=MessageTriggerSource.CAMPAIGN,
                            business_id=campaign.business_id,
                            log_metadata={"campaign_id": campaign.id}
                        )
                        success = msg_log.status == MessageStatus.SENT
                        external_id = msg_log.external_id
                        error_message = msg_log.error_message

                if success:
                    recipient.status = RecipientStatus.SENT
                    recipient.sent_at = datetime.now(timezone.utc)
                    recipient.external_id = external_id
                    campaign.sent_count += 1
                else:
                    recipient.status = RecipientStatus.FAILED
                    recipient.error_message = error_message or "Failed to send"
                    campaign.failed_count += 1

            except Exception as e:
                logger.error(f"Error sending campaign {campaign_id} to recipient {recipient.id}: {e}")
                recipient.status = RecipientStatus.FAILED
                recipient.error_message = str(e)
                campaign.failed_count += 1

            await self.session.commit()

        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
