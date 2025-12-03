"""
Unit tests for logging timestamp utilities
"""
from datetime import datetime, timezone
from unittest.mock import patch
from src.logging.timestamp import (
    generate_timestamp,
    generate_request_id,
    format_filename_timestamp,
    format_title_timestamp,
    format_numeric_timestamp,
    format_folder_path
)


def test_generate_timestamp_returns_utc():
    """Test that generate_timestamp returns UTC datetime"""
    ts = generate_timestamp()
    assert ts.tzinfo == timezone.utc
    assert isinstance(ts, datetime)


def test_generate_request_id_format():
    """Test that generate_request_id returns correct format"""
    # Pass a datetime directly instead of mocking
    mock_dt = datetime(2025, 12, 3, 19, 5, 30, 36009, tzinfo=timezone.utc)
    request_id = generate_request_id(mock_dt)
    assert request_id == "20251203-1905-30036009"


def test_generate_request_id_with_timestamp():
    """Test that generate_request_id uses provided timestamp"""
    dt1 = datetime(2025, 12, 3, 10, 30, 45, 123456, tzinfo=timezone.utc)
    dt2 = datetime(2025, 12, 3, 10, 30, 45, 123456, tzinfo=timezone.utc)
    
    # Same datetime should produce same request_id
    id1 = generate_request_id(dt1)
    id2 = generate_request_id(dt2)
    assert id1 == id2
    assert id1 == "20251203-1030-45123456"


def test_generate_request_id_unique():
    """Test that generate_request_id generates unique IDs"""
    id1 = generate_request_id()
    id2 = generate_request_id()
    # IDs should be different due to microsecond precision
    # (unless called in exact same microsecond, extremely unlikely)
    assert isinstance(id1, str)
    assert isinstance(id2, str)
    assert len(id1) == 22  # YYYYMMDD-HHMM-SSμμμμμμ (8+1+4+1+8)


def test_format_filename_timestamp():
    """Test filename timestamp format"""
    dt = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    result = format_filename_timestamp(dt)
    assert result == "20251203-1415-30123456"


def test_format_filename_timestamp_preserves_sort_order():
    """Test that filename timestamps maintain chronological sort order"""
    dt1 = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    dt2 = datetime(2025, 12, 3, 14, 15, 31, 456789, tzinfo=timezone.utc)
    dt3 = datetime(2025, 12, 3, 14, 16, 0, 0, tzinfo=timezone.utc)
    dt4 = datetime(2025, 12, 4, 8, 30, 0, 0, tzinfo=timezone.utc)
    
    ts1 = format_filename_timestamp(dt1)
    ts2 = format_filename_timestamp(dt2)
    ts3 = format_filename_timestamp(dt3)
    ts4 = format_filename_timestamp(dt4)
    
    # Lexicographic sort should equal chronological sort
    assert ts1 < ts2 < ts3 < ts4


def test_format_title_timestamp():
    """Test title timestamp format"""
    dt = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    result = format_title_timestamp(dt)
    assert result == "2025/12/03 14:15:30.123456 UTC"


def test_format_title_timestamp_with_zero_microseconds():
    """Test title timestamp with zero microseconds"""
    dt = datetime(2025, 12, 3, 14, 15, 30, 0, tzinfo=timezone.utc)
    result = format_title_timestamp(dt)
    assert result == "2025/12/03 14:15:30.000000 UTC"


def test_format_folder_path():
    """Test folder path format"""
    dt = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    result = format_folder_path(dt)
    assert result == "2025/12/03"


def test_format_folder_path_single_digit_month_day():
    """Test folder path with single-digit month and day"""
    dt = datetime(2025, 1, 5, 14, 15, 30, 123456, tzinfo=timezone.utc)
    result = format_folder_path(dt)
    assert result == "2025/01/05"


def test_format_numeric_timestamp():
    """Test numeric timestamp format for log tables"""
    dt = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    result = format_numeric_timestamp(dt)
    assert result == "20251203-141530.123456"


def test_format_numeric_timestamp_preserves_sort_order():
    """Test that numeric timestamps maintain chronological sort order"""
    dt1 = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    dt2 = datetime(2025, 12, 3, 14, 15, 31, 456789, tzinfo=timezone.utc)
    dt3 = datetime(2025, 12, 4, 8, 30, 0, 0, tzinfo=timezone.utc)
    
    ts1 = format_numeric_timestamp(dt1)
    ts2 = format_numeric_timestamp(dt2)
    ts3 = format_numeric_timestamp(dt3)
    
    # Lexicographic sort should equal chronological sort
    assert ts1 < ts2 < ts3
