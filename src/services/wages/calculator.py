from typing import Dict, Any, Type
from src.models import WageConfiguration, WageModelType
from src.services.wages.strategy import WageStrategy
from src.services.wages.strategies import (
    CommissionStrategy,
    HourlyJobStrategy,
    HourlyShiftStrategy,
    FixedDailyStrategy,
)

class WageCalculator:
    _strategies: Dict[WageModelType, Type[WageStrategy]] = {
        WageModelType.COMMISSION: CommissionStrategy,
        WageModelType.HOURLY_PER_JOB: HourlyJobStrategy,
        WageModelType.HOURLY_PER_SHIFT: HourlyShiftStrategy,
        WageModelType.FIXED_DAILY: FixedDailyStrategy,
    }

    @classmethod
    def calculate_wage(cls, config: WageConfiguration, context: Dict[str, Any]) -> float:
        """
        Calculates the wage for an employee based on their configuration and the current context.
        """
        strategy_class = cls._strategies.get(config.model_type)
        if not strategy_class:
            raise ValueError(f"No strategy found for wage model type: {config.model_type}")
        
        strategy = strategy_class()
        return strategy.calculate(config, context)
