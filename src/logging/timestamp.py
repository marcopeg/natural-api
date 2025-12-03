"""
Timestamp utilities for logging system
"""
from datetime import datetime, timezone


def generate_timestamp() -> datetime:
    """
    Generate current UTC timestamp.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def format_filename_timestamp(dt: datetime) -> str:
    """
    Format timestamp for log filename.
    
    Format: YYYYMMDD-HHMM-SSμμμμμμ
    Example: 20251203-1415-30123456
    
    Args:
        dt: Datetime to format (should be UTC)
        
    Returns:
        str: Formatted timestamp for filename
    """
    return (
        dt.strftime("%Y%m%d-%H%M-") +  # Date and time with separators
        dt.strftime("%S") +             # Seconds
        f"{dt.microsecond:06d}"         # Microseconds (6 digits)
    )


def format_title_timestamp(dt: datetime) -> str:
    """
    Format timestamp for log file title (human-readable).
    
    Format: YYYY/MM/DD HH:MM:SS.μμμμμμ UTC
    Example: 2025/12/03 14:15:30.123456 UTC
    
    Args:
        dt: Datetime to format (should be UTC)
        
    Returns:
        str: Formatted timestamp for display
    """
    return dt.strftime("%Y/%m/%d %H:%M:%S") + f".{dt.microsecond:06d} UTC"


def format_numeric_timestamp(dt: datetime) -> str:
    """
    Format timestamp as compact numeric string for log tables.
    
    Format: YYYYMMDD-HHMMSS.μμμμμμ
    Example: 20251203-142530.123456
    
    Args:
        dt: Datetime to format (should be UTC)
        
    Returns:
        str: Compact numeric timestamp
    """
    return dt.strftime("%Y%m%d-%H%M%S") + f".{dt.microsecond:06d}"


def format_folder_path(dt: datetime) -> str:
    """
    Format timestamp for folder path.
    
    Format: YYYY/MM/DD
    Example: 2025/12/03
    
    Args:
        dt: Datetime to format (should be UTC)
        
    Returns:
        str: Formatted path for log directory
    """
    return dt.strftime("%Y/%m/%d")
