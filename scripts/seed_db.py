import asyncio
from src.database import engine, Base, AsyncSessionLocal
from src.models import Business, User, UserRole


async def seed():
    async with engine.begin() as conn:
        # This will recreate tables
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create a business
        business = Business(name="Test Business")
        session.add(business)
        await session.flush()

        # Create a user
        user = User(
            phone_number="1234567890",
            business_id=business.id,
            role=UserRole.OWNER,
            preferences={"confirm_by_default": False},
        )
        session.add(user)
        await session.commit()
        print("Database seeded successfully with user 1234567890.")


if __name__ == "__main__":
    asyncio.run(seed())
