from typing import Optional
from datetime import timezone
from src.services.time_tracking import TimeTrackingService
from src.uimodels import CheckInTool, CheckOutTool


class ShiftTools:
    def __init__(self, service: TimeTrackingService):
        self.service = service

    async def check_in(self, tool: CheckInTool, user_id: int) -> str:
        try:
            user = await self.service.check_in(user_id)
            # Ensure safe access to current_shift_start
            time_str = "Unknown"
            if user.current_shift_start:
                # Ensure aware
                start = user.current_shift_start
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                time_str = start.strftime("%H:%M")

            return f"Checked in at {time_str}"
        except ValueError as e:
            return f"Error: {str(e)}"

    async def check_out(
        self, tool: CheckOutTool, user_id: int
    ) -> tuple[str, Optional[dict]]:
        try:
            user, start, end, jobs = await self.service.check_out(user_id)
            duration = end - start
            hours = duration.total_seconds() / 3600

            # Format jobs for the UI
            job_list = []
            for j in jobs:
                job_list.append(
                    {
                        "id": j.id,
                        "description": j.description,
                        "customer_name": j.customer.name if j.customer else "Unknown",
                        "location": j.location,
                        "duration_seconds": j.total_actual_duration_seconds,
                    }
                )

            summary = f"Checked out. Shift duration: {hours:.2f} hours."
            card_data = {
                "tool": "CheckOutTool",
                "duration": f"{int(hours)}h {int((hours % 1) * 60)}m",
                "verified": True,  # Shimmed as per designer
                "jobs": job_list,
                "end_time": end.isoformat(),
            }

            return summary, card_data
        except ValueError as e:
            return f"Error: {str(e)}", None
