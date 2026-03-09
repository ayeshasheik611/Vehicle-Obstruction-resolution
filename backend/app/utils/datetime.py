"""
DateTime utilities for IST (Indian Standard Time)
All datetime operations should use IST instead of UTC
"""
from datetime import datetime, timedelta
import pytz

# IST timezone
IST = pytz.timezone('Asia/Kolkata')


def now_ist() -> datetime:
    """Get current datetime in IST (naive datetime, no timezone info)"""
    # Get current time in IST and return as naive datetime
    return datetime.now(IST).replace(tzinfo=None)


def utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(IST).replace(tzinfo=None)


def ist_to_utc(ist_dt: datetime) -> datetime:
    """Convert IST datetime to UTC"""
    if ist_dt.tzinfo is None:
        ist_dt = IST.localize(ist_dt)
    return ist_dt.astimezone(pytz.utc).replace(tzinfo=None)


def format_ist(dt: datetime) -> str:
    """Format datetime in IST for display"""
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    elif dt.tzinfo != IST:
        dt = dt.astimezone(IST)
    return dt.strftime('%d/%m/%Y, %I:%M %p IST')
