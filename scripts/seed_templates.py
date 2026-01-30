import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.database import Base, DATABASE_URL
from src.models import (
    WhatsAppTemplate,
    WhatsAppTemplateStatus,
    WhatsAppTemplateCategory,
    Business,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default templates to seed (mirrors DEFAULT_TEMPLATES from frontend)
DEFAULT_TEMPLATES = [
    {
        "name": "Job Booked Confirmation",
        "category": WhatsAppTemplateCategory.UTILITY,
        "components": [
            {
                "type": "BODY",
                "text": "Hi {{customer.first_name}}, your appointment is confirmed for {{job.date}} at {{job.time}}. Reply YES to confirm or RESCHEDULE if you need to make changes.",
            }
        ],
        "language": "en_US",
    },
    {
        "name": "Technician On My Way",
        "category": WhatsAppTemplateCategory.UTILITY,
        "components": [
            {
                "type": "BODY",
                "text": "Hi {{customer.first_name}}, {{technician.name}} is on the way to your property! Expected arrival time: {{arrival.time}}.",
            }
        ],
        "language": "en_US",
    },
    {
        "name": "Job Completed & Invoice",
        "category": WhatsAppTemplateCategory.UTILITY,
        "components": [
            {
                "type": "BODY",
                "text": "Hi {{customer.first_name}}, thanks for choosing {{business.name}}! Your job has been completed. You can view and pay your invoice here: {{invoice.link}}",
            }
        ],
        "language": "en_US",
    },
    {
        "name": "Review Request",
        "category": WhatsAppTemplateCategory.MARKETING,
        "components": [
            {
                "type": "BODY",
                "text": "Hi {{customer.first_name}}, we hope you were happy with our service! Would you mind taking 30 seconds to leave us a review? It helps a lot! {{review.link}}",
            }
        ],
        "language": "en_US",
    },
]


async def seed_templates():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # Get all businesses to seed for
        result = await session.execute(select(Business))
        businesses = result.scalars().all()

        if not businesses:
            logger.warning("No businesses found to seed templates for.")
            return

        for business in businesses:
            logger.info(
                f"Seeding templates for business: {business.name} (ID: {business.id})"
            )

            for tmpl_data in DEFAULT_TEMPLATES:
                # Check if template explicitly exists by name
                stmt = select(WhatsAppTemplate).where(
                    WhatsAppTemplate.business_id == business.id,
                    WhatsAppTemplate.name == tmpl_data["name"],
                )
                existing = await session.execute(stmt)
                if existing.scalar_one_or_none():
                    logger.info(
                        f"  - Template '{tmpl_data['name']}' already exists. Skipping."
                    )
                    continue

                # Create new template
                new_template = WhatsAppTemplate(
                    business_id=business.id,
                    name=tmpl_data["name"],
                    category=tmpl_data["category"],
                    components=tmpl_data["components"],
                    language=tmpl_data["language"],
                    status=WhatsAppTemplateStatus.DRAFT,  # Start as DRAFT locally
                    meta_template_id=None,
                )
                session.add(new_template)
                logger.info(f"  - Created template '{tmpl_data['name']}'")

        await session.commit()

    await engine.dispose()
    logger.info("Template seeding completed.")


if __name__ == "__main__":
    asyncio.run(seed_templates())
