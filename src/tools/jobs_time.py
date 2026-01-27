from datetime import timezone
from src.services.time_tracking import TimeTrackingService
from src.uimodels import StartJobTool, FinishJobTool

class JobTimeTools:
    def __init__(self, service: TimeTrackingService):
        self.service = service

    async def start_job(self, tool: StartJobTool, user_id: int) -> str:
        try:
            job = await self.service.start_job(tool.job_id, user_id)
            time_str = "Unknown"
            if job.begun_at:
                start = job.begun_at
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                time_str = start.strftime("%H:%M")
            return f"Job {job.id} started at {time_str}"
        except ValueError as e:
            return f"Error: {str(e)}"

    async def finish_job(self, tool: FinishJobTool) -> str:
        try:
            job, total_seconds = await self.service.finish_job(tool.job_id)
            minutes = total_seconds / 60
            return f"Job {job.id} finished. Total duration: {minutes:.0f} minutes."
        except ValueError as e:
            return f"Error: {str(e)}"
