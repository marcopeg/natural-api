"""
Log file writer
"""
from pathlib import Path
from src.logging.models import LogEntry
from src.logging.formatter import format_log_markdown
from src.config import config


def write_log(entry: LogEntry, file_request_id: str | None = None) -> Path:
    """
    Write log entry to disk.
    
    Args:
        entry: LogEntry to write
        file_request_id: Optional custom request ID for filename (defaults to timestamp-based)
        
    Returns:
        Path: Path to written log file
        
    Raises:
        IOError: If log write fails
    """
    log_path = config.get_log_file_path(entry.timestamp, entry.status_code, file_request_id)
    log_content = format_log_markdown(entry)
    
    try:
        log_path.write_text(log_content, encoding='utf-8')
        return log_path
    except Exception as e:
        raise IOError(f"Failed to write log file: {e}") from e
