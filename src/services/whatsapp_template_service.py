import logging
import httpx
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import WhatsAppTemplate, WhatsAppTemplateStatus, WhatsAppTemplateCategory
from src.config import settings

logger = logging.getLogger(__name__)

class WhatsAppTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.api_version = settings.whatsapp_api_version
        self.access_token = settings.whatsapp_access_token
        self.waba_id = settings.waba_id

    async def create_template(
        self,
        business_id: int,
        name: str,
        category: WhatsAppTemplateCategory,
        components: List[dict],
        language: str = "en_US"
    ) -> WhatsAppTemplate:
        # 1. Create local record
        template = WhatsAppTemplate(
            business_id=business_id,
            name=name,
            category=category,
            components=components,
            language=language,
            status=WhatsAppTemplateStatus.PENDING
        )
        self.session.add(template)
        await self.session.flush()

        # 2. Call Meta API
        if not self.access_token or not self.waba_id:
             logger.warning("WhatsApp settings missing. Template created locally only.")
             return template

        url = f"https://graph.facebook.com/{self.api_version}/{self.waba_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": name,
            "category": category.value,
            "components": components,
            "language": language,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    template.meta_template_id = data.get("id")
                    template.status = WhatsAppTemplateStatus.PENDING # Always pending review initially
                else:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Meta API Error: {error_msg}")
                    template.status = WhatsAppTemplateStatus.REJECTED
                    template.rejection_reason = error_msg
            except Exception as e:
                logger.error(f"Exception creating template: {e}")
                template.status = WhatsAppTemplateStatus.DRAFT # Failed to submit
                template.rejection_reason = str(e)
        
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def sync_templates(self, business_id: int):
        if not self.access_token or not self.waba_id:
            logger.warning("WhatsApp settings missing. Cannot sync templates.")
            return

        url = f"https://graph.facebook.com/{self.api_version}/{self.waba_id}/message_templates"
        params = {"fields": "id,status,name,language,category,components,rejected_reason"}
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch templates: {response.text}")
                    return

                data = response.json()
                remote_templates = data.get("data", [])
                
                for rt in remote_templates:
                    meta_id = rt.get("id")
                    status_map = {
                        "APPROVED": WhatsAppTemplateStatus.APPROVED,
                        "REJECTED": WhatsAppTemplateStatus.REJECTED,
                        "PENDING": WhatsAppTemplateStatus.PENDING,
                        "PAUSED": WhatsAppTemplateStatus.PAUSED,
                        "DISABLED": WhatsAppTemplateStatus.DISABLED,
                        "PENDING_DELETION": WhatsAppTemplateStatus.DISABLED
                    }
                    
                    # Try to find by meta_id
                    stmt = select(WhatsAppTemplate).where(
                        WhatsAppTemplate.business_id == business_id,
                        WhatsAppTemplate.meta_template_id == meta_id
                    )
                    result = await self.session.execute(stmt)
                    local_tmpl = result.scalar_one_or_none()
                    
                    if not local_tmpl:
                        # Fallback: match by name & language
                        stmt = select(WhatsAppTemplate).where(
                            WhatsAppTemplate.business_id == business_id,
                            WhatsAppTemplate.name == rt.get("name"),
                            WhatsAppTemplate.language == rt.get("language")
                        )
                        result = await self.session.execute(stmt)
                        local_tmpl = result.scalar_one_or_none()

                    if local_tmpl:
                        # Update existing
                        new_status = status_map.get(rt.get("status"), WhatsAppTemplateStatus.DRAFT)
                        if local_tmpl.status != new_status:
                            local_tmpl.status = new_status
                        
                        local_tmpl.meta_template_id = meta_id
                        local_tmpl.rejection_reason = rt.get("rejected_reason")
                        # Optionally update components
                        local_tmpl.components = rt.get("components")
                    else:
                        # Create new from remote
                        new_tmpl = WhatsAppTemplate(
                            business_id=business_id,
                            name=rt.get("name"),
                            language=rt.get("language"),
                            category=WhatsAppTemplateCategory(rt.get("category")) if rt.get("category") in WhatsAppTemplateCategory.__members__ else WhatsAppTemplateCategory.UTILITY,
                            components=rt.get("components"),
                            status=status_map.get(rt.get("status"), WhatsAppTemplateStatus.DRAFT),
                            meta_template_id=meta_id,
                            rejection_reason=rt.get("rejected_reason")
                        )
                        self.session.add(new_tmpl)
                
                await self.session.commit()
            except Exception as e:
                logger.error(f"Error syncing templates: {e}")
