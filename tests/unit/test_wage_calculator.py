import pytest
from datetime import datetime
from src.models import WageConfiguration, WageModelType
from src.services.wages.calculator import WageCalculator


def test_commission_calculation():
    config = WageConfiguration(
        model_type=WageModelType.COMMISSION,
        rate_value=10.0,  # 10%
    )
    context = {"job_revenue": 500.0}

    amount = WageCalculator.calculate_wage(config, context)
    assert amount == 50.0


def test_hourly_per_job_calculation():
    config = WageConfiguration(
        model_type=WageModelType.HOURLY_PER_JOB,
        rate_value=20.0,  # $20/hr
    )
    start = datetime(2026, 1, 22, 10, 0)
    end = datetime(2026, 1, 22, 11, 30)  # 1.5 hours
    context = {"start_time": start, "end_time": end}

    amount = WageCalculator.calculate_wage(config, context)
    assert amount == 30.0


def test_hourly_per_shift_calculation():
    config = WageConfiguration(
        model_type=WageModelType.HOURLY_PER_SHIFT,
        rate_value=25.0,  # $25/hr
    )
    start = datetime(2026, 1, 22, 8, 0)
    end = datetime(2026, 1, 22, 16, 0)  # 8 hours
    context = {"shift_start": start, "shift_end": end}

    amount = WageCalculator.calculate_wage(config, context)
    assert amount == 200.0


def test_fixed_daily_calculation():
    config = WageConfiguration(
        model_type=WageModelType.FIXED_DAILY,
        rate_value=150.0,  # $150 per day
    )
    context = {}  # context not needed for fixed

    amount = WageCalculator.calculate_wage(config, context)
    assert amount == 150.0


def test_hourly_rounding():
    config = WageConfiguration(model_type=WageModelType.HOURLY_PER_JOB, rate_value=20.0)
    start = datetime(2026, 1, 22, 10, 0)
    end = datetime(2026, 1, 22, 10, 10)  # 1/6 hour = 3.333...
    context = {"start_time": start, "end_time": end}

    amount = WageCalculator.calculate_wage(config, context)
    # 20 * (10/60) = 20/6 = 3.3333... rounds to 3.33
    assert amount == 3.33


def test_missing_context_keys():
    config = WageConfiguration(model_type=WageModelType.COMMISSION, rate_value=10.0)
    with pytest.raises(KeyError) as excinfo:
        WageCalculator.calculate_wage(config, {})
    assert "job_revenue" in str(excinfo.value)

    config_hourly = WageConfiguration(
        model_type=WageModelType.HOURLY_PER_JOB, rate_value=20.0
    )
    with pytest.raises(KeyError) as excinfo:
        WageCalculator.calculate_wage(config_hourly, {"start_time": datetime.now()})
    assert "end_time" in str(excinfo.value)


def test_negative_duration():
    config = WageConfiguration(model_type=WageModelType.HOURLY_PER_JOB, rate_value=20.0)
    start = datetime(2026, 1, 22, 11, 0)
    end = datetime(2026, 1, 22, 10, 0)
    context = {"start_time": start, "end_time": end}

    amount = WageCalculator.calculate_wage(config, context)
    assert amount == 0.0
