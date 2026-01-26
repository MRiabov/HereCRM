import asyncio
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.database import AsyncSessionLocal

from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool
from src.repositories import JobRepository, UserRepository
from src.services.template_service import TemplateService

async def verify():
    async with AsyncSessionLocal() as session:
        # 1. Setup context
        # Need a business and user. assuming business_id 1 exists.
        business_id = 1
        
        # Get a user to act as executor
        repo = UserRepository(session)
        users = await repo.get_all(business_id)
        if not users:
            print("No users found to test with.")
            return
        user = users[0]
        
        print(f"Testing with User: {user.name} (ID: {user.id})")

        executor = ToolExecutor(
            session=session,
            business_id=business_id,
            user_id=user.id,
            user_phone=user.phone_number,
            template_service=TemplateService()
        )

        # 2. Execute AddJobTool with estimated_duration
        print("Executing AddJobTool with estimated_duration=120...")
        tool = AddJobTool(
            customer_name="Test Duration Customer",
            description="Test Job for Duration",
            price=100.0,
            estimated_duration=120,
            time="tomorrow at 10am" # Just for logical consistency, actual scheduling might vary
        )
        
        result_text, result_data = await executor.execute(tool)
        print(f"Tool Result: {result_text}")
        
        if not result_data:
            print("Failed: No result data returned.")
            return

        job_id = result_data.get("id")
        if not job_id:
             print("Failed: No job ID returned.")
             return
             
        # 3. Verify Job in DB
        job_repo = JobRepository(session)
        job = await job_repo.get_by_id(job_id, business_id)
        
        if not job:
            print(f"Failed: Job {job_id} not found in DB.")
            return
            
        print(f"Job Created: ID={job.id}")
        print(f"Job Estimated Duration: {job.estimated_duration}")
        
        if job.estimated_duration == 120:
            print("SUCCESS: estimated_duration was correctly saved as 120.")
        else:
            print(f"FAILURE: estimated_duration mismatch. Expected 120, got {job.estimated_duration}")

if __name__ == "__main__":
    asyncio.run(verify())
