from datetime import datetime
from typing import Dict, Any
from src.models import WageConfiguration
from src.services.wages.strategy import WageStrategy

class CommissionStrategy(WageStrategy):
    def calculate(self, config: WageConfiguration, context: Dict[str, Any]) -> float:
        job_revenue = context.get("job_revenue")
        if job_revenue is None:
            raise KeyError("CommissionStrategy requires 'job_revenue' in context")
        
        amount = job_revenue * (config.rate_value / 100.0)
        return round(amount, 2)

class HourlyJobStrategy(WageStrategy):
    def calculate(self, config: WageConfiguration, context: Dict[str, Any]) -> float:
        start_time = context.get("start_time")
        end_time = context.get("end_time")
        
        if not start_time or not end_time:
            raise KeyError("HourlyJobStrategy requires 'start_time' and 'end_time' in context")
        
        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600.0
        
        if duration_hours < 0:
            return 0.0
            
        amount = duration_hours * config.rate_value
        return round(amount, 2)

class HourlyShiftStrategy(WageStrategy):
    def calculate(self, config: WageConfiguration, context: Dict[str, Any]) -> float:
        shift_start = context.get("shift_start")
        shift_end = context.get("shift_end")
        
        if not shift_start or not shift_end:
            raise KeyError("HourlyShiftStrategy requires 'shift_start' and 'shift_end' in context")
            
        duration = shift_end - shift_start
        duration_hours = duration.total_seconds() / 3600.0
        
        if duration_hours < 0:
            return 0.0
            
        amount = duration_hours * config.rate_value
        return round(amount, 2)

class FixedDailyStrategy(WageStrategy):
    def calculate(self, config: WageConfiguration, context: Dict[str, Any]) -> float:
        # Fixed sum per check-in / day.
        # We assume if calculate is called, the condition for the fixed payment (e.g. check-in) is met.
        return round(config.rate_value, 2)
