"""
PICAM Time Utilities
Consistent time handling across the system
"""

from datetime import datetime, date, timedelta, timezone
from typing import Tuple, Optional
import pytz


# System timezone (configurable)
SYSTEM_TIMEZONE = pytz.UTC


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def today_utc() -> date:
    """Get current UTC date."""
    return now_utc().date()


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC.
    If naive, assume UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_date_range(
    start_date: date,
    end_date: date
) -> Tuple[datetime, datetime]:
    """
    Convert date range to datetime range (start of start_date to end of end_date).
    """
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
    return start_dt, end_dt


def get_observation_periods(
    start_time: datetime,
    end_time: datetime,
    period_seconds: int = 300
) -> list:
    """
    Generate list of observation period start times.
    
    Args:
        start_time: Period start
        end_time: Period end
        period_seconds: Length of each period
        
    Returns:
        List of period start datetimes
    """
    periods = []
    current = start_time
    delta = timedelta(seconds=period_seconds)
    
    while current < end_time:
        periods.append(current)
        current += delta
        
    return periods


def seconds_to_readable(seconds: float) -> str:
    """
    Convert seconds to human-readable string.
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def get_hour_of_day(dt: datetime) -> int:
    """Get hour of day (0-23) in UTC."""
    return to_utc(dt).hour


def get_day_of_week(dt: datetime) -> int:
    """Get day of week (0=Monday, 6=Sunday)."""
    return to_utc(dt).weekday()


def is_peak_hour(dt: datetime, peak_hours: list = None) -> bool:
    """
    Check if datetime falls within peak hours.
    Default peak hours: 8-10 AM, 2-6 PM for hotels.
    """
    if peak_hours is None:
        peak_hours = list(range(8, 11)) + list(range(14, 18))
    
    hour = get_hour_of_day(dt)
    return hour in peak_hours


def aggregate_by_hour(data_points: list, timestamp_field: str = "timestamp") -> dict:
    """
    Group data points by hour.
    
    Returns:
        Dict with hour (0-23) as key, list of data points as value
    """
    by_hour = {h: [] for h in range(24)}
    
    for dp in data_points:
        ts = dp.get(timestamp_field) if isinstance(dp, dict) else getattr(dp, timestamp_field)
        hour = get_hour_of_day(ts)
        by_hour[hour].append(dp)
        
    return by_hour


def aggregate_by_date(data_points: list, timestamp_field: str = "timestamp") -> dict:
    """
    Group data points by date.
    
    Returns:
        Dict with date as key, list of data points as value
    """
    by_date = {}
    
    for dp in data_points:
        ts = dp.get(timestamp_field) if isinstance(dp, dict) else getattr(dp, timestamp_field)
        d = to_utc(ts).date()
        
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(dp)
        
    return by_date