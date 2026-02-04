import asyncio
import time
import os
import sys
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set dummy env vars to avoid pydantic validation errors
os.environ["WHATSAPP_APP_SECRET"] = "dummy"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from src.database import Base
from src.models import Business, Customer, Job, Quote, QuoteStatus
import logging

# Suppress SQLAlchemy logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

async def run_benchmark():
    # Use in-memory SQLite for benchmark
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("Seeding database...")
    async with SessionLocal() as session:
        # Create Business
        business = Business(name="Benchmark Business")
        session.add(business)
        await session.flush()

        # Create Customer
        customer = Customer(business_id=business.id, name="Test Customer")
        session.add(customer)
        await session.flush()

        # Create 5000 Jobs
        jobs = []
        for i in range(5000):
            job = Job(
                business_id=business.id,
                customer_id=customer.id,
                description=f"Job {i}",
            )
            jobs.append(job)
        session.add_all(jobs)
        await session.flush()

        job_ids = [j.id for j in jobs]

        # Create 5000 Quotes, linked to Jobs
        quotes = []
        for job_id in job_ids:
            quote = Quote(
                business_id=business.id,
                customer_id=customer.id,
                job_id=job_id,
                status=QuoteStatus.DRAFT,
                total_amount=100.0,
                external_token=f"token_{job_id}"
            )
            quotes.append(quote)
        session.add_all(quotes)
        await session.commit()

        print(f"Seeded {len(jobs)} jobs and {len(quotes)} quotes.")

    print("Running benchmark queries...")

    # We will look up quotes by job_id
    # We shuffle job_ids to avoid any sequential caching benefit (though unlikely in sqlite memory in this way)
    random.shuffle(job_ids)

    start_time = time.perf_counter()

    query_count = 0
    async with SessionLocal() as session:
        # Measure looking up quote for each job
        for job_id in job_ids:
            stmt = select(Quote).where(Quote.job_id == job_id)
            result = await session.execute(stmt)
            _ = result.scalars().first()
            query_count += 1

    end_time = time.perf_counter()
    duration = end_time - start_time
    avg_per_query = (duration / query_count) * 1000  # ms

    print("\nBenchmark Results:")
    print(f"Total time: {duration:.4f} seconds")
    print(f"Total queries: {query_count}")
    print(f"Average time per query: {avg_per_query:.4f} ms")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_benchmark())
