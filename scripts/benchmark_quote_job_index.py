import sys
import os
import time
import random
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Add current directory to path so we can import src
sys.path.append(os.getcwd())

# Suppress logging
logging.basicConfig(level=logging.WARNING, force=True)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Mock environment variables if needed
os.environ["CRON_SECRET"] = "test"
os.environ["OPENAI_API_KEY"] = "test"
# Use a valid async URL for the app initialization to avoid crash on import
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

try:
    from src.database import Base
    from src.models import Job, Quote, Business, Customer
except ImportError as e:
    print(f"Error importing models: {e}")
    sys.exit(1)

def benchmark():
    print("Setting up database...")
    # Use a separate synchronous in-memory SQLite database for the benchmark
    # We don't use the engine from src.database because it's async
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Create dependencies
        business = Business(name="Test Business")
        session.add(business)
        session.flush()

        customer = Customer(business_id=business.id, name="Test Customer")
        session.add(customer)
        session.flush()

        # Create a large number of jobs
        print("Seeding 1,000 Jobs...")
        jobs = []
        for i in range(1000):
            job = Job(business_id=business.id, customer_id=customer.id, status="PENDING")
            jobs.append(job)
        session.add_all(jobs)
        session.flush()

        # Create a large number of quotes
        print("Seeding 20,000 Quotes...")
        quotes = []
        for i in range(20000):
            # Randomly assign a job_id (some null, some set)
            # We want a distribution where we can query for specific job_ids
            job_id = jobs[i % 1000].id
            quote = Quote(
                business_id=business.id,
                customer_id=customer.id,
                job_id=job_id,
                external_token=f"token_{i}"
            )
            quotes.append(quote)
        session.add_all(quotes)
        session.commit()
        print("Seeding complete.")

        # Benchmark
        print("Running benchmark (SELECT Quote WHERE job_id = X)...")
        start_time = time.time()
        iterations = 1000

        # Query for different job_ids to avoid caching effects if any (though session cache is relevant here)
        # We use a new session for querying or expire all to ensure we hit the DB
        session.expire_all()

        for i in range(iterations):
            target_job_id = jobs[i % 1000].id
            stmt = select(Quote).where(Quote.job_id == target_job_id)
            # Execute and fetch
            _ = session.scalars(stmt).all()

        end_time = time.time()
        duration = end_time - start_time
        print(f"Total time for {iterations} queries: {duration:.4f} seconds")
        print(f"Average time per query: {duration/iterations:.6f} seconds")

if __name__ == "__main__":
    benchmark()
