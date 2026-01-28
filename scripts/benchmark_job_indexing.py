import asyncio
import time
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from src.database import Base
from src.models import Business, Customer, Job, PipelineStage
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

        # Create Customers
        customers = []
        for i in range(100):
            customer = Customer(
                business_id=business.id,
                name=f"Customer {i}",
                pipeline_stage=PipelineStage.NOT_CONTACTED
            )
            customers.append(customer)
        session.add_all(customers)
        await session.flush()

        # Create Jobs (100 per customer = 10,000 jobs)
        jobs = []
        for customer in customers:
            for j in range(100):
                job = Job(
                    business_id=business.id,
                    customer_id=customer.id,
                    description=f"Job {j} for {customer.name}",
                    status="pending"
                )
                jobs.append(job)
        session.add_all(jobs)
        await session.commit()

        customer_ids = [c.id for c in customers]
        print(f"Seeded {len(customers)} customers and {len(jobs)} jobs.")

    print("Running benchmark queries...")
    start_time = time.perf_counter()

    query_count = 0
    async with SessionLocal() as session:
        # Measure looking up jobs for each customer
        # Repeat 5 times to get a stable measurement
        for _ in range(5):
            for customer_id in customer_ids:
                stmt = select(Job).where(Job.customer_id == customer_id)
                result = await session.execute(stmt)
                _ = result.scalars().all()
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
