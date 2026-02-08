"""
Timezone utilities for Grayco Lite V3.

This module provides centralized timezone handling for the application,
ensuring all datetime operations use Mountain Time (America/Denver).
"""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# Mountain Time timezone (handles DST automatically)
MOUNTAIN_TZ = ZoneInfo("America/Denver")
UTC_TZ = ZoneInfo("UTC")


def now_mountain() -> datetime:
    """Get current datetime in Mountain Time.
    
    Returns:
        datetime: Current datetime localized to America/Denver timezone.
    """
    return datetime.now(MOUNTAIN_TZ)


def today_mountain() -> date:
    """Get current date in Mountain Time.
    
    Returns:
        date: Current date in America/Denver timezone.
    """
    return datetime.now(MOUNTAIN_TZ).date()


def localize_to_mountain(dt: datetime) -> datetime:
    """Convert a datetime to Mountain Time.
    
    Args:
        dt: A datetime object (naive or aware).
        
    Returns:
        datetime: The datetime converted to Mountain Time.
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=UTC_TZ)
    
    return dt.astimezone(MOUNTAIN_TZ)


def format_mountain_time(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format a datetime in Mountain Time.
    
    Args:
        dt: A datetime object to format.
        fmt: strftime format string.
        
    Returns:
        str: Formatted datetime string in Mountain Time.
    """
    if dt is None:
        return ""
    
    mountain_dt = localize_to_mountain(dt)
    return mountain_dt.strftime(fmt)


def is_today_mountain(dt: datetime | date) -> bool:
    """Check if a datetime/date is today in Mountain Time.
    
    Args:
        dt: A datetime or date object to check.
        
    Returns:
        bool: True if the date is today in Mountain Time.
    """
    if dt is None:
        return False
    
    today = today_mountain()
    
    if isinstance(dt, datetime):
        dt = dt.date()
    
    return dt == today


def is_overdue_mountain(dt: datetime | date) -> bool:
    """Check if a datetime/date is overdue (before today) in Mountain Time.
    
    Args:
        dt: A datetime or date object to check.
        
    Returns:
        bool: True if the date is before today in Mountain Time.
    """
    if dt is None:
        return False
    
    today = today_mountain()
    
    if isinstance(dt, datetime):
        dt = dt.date()
    
    return dt < today


def days_until_mountain(dt: datetime | date) -> int:
    """Calculate days until a date from today in Mountain Time.
    
    Args:
        dt: A datetime or date object.
        
    Returns:
        int: Number of days until the date (negative if past).
    """
    if dt is None:
        return 0
    
    today = today_mountain()
    
    if isinstance(dt, datetime):
        dt = dt.date()
    
    return (dt - today).days


def get_timestamp_mountain() -> str:
    """Get a formatted timestamp string in Mountain Time.
    
    Returns:
        str: Current timestamp formatted as YYYY-MM-DD HH:MM.
    """
    return now_mountain().strftime("%Y-%m-%d %H:%M")


def get_file_timestamp_mountain() -> str:
    """Get a file-safe timestamp string in Mountain Time.
    
    Returns:
        str: Current timestamp formatted as YYYYMMDD_HHMMSS.
    """
    return now_mountain().strftime("%Y%m%d_%H%M%S")
