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

    async def check_out(self, tool: CheckOutTool, user_id: int) -> str:
        try:
            user, start, end = await self.service.check_out(user_id)
            duration = end - start
            hours = duration.total_seconds() / 3600
            return f"Checked out. Shift duration: {hours:.2f} hours."
        except ValueError as e:
            return f"Error: {str(e)}"
