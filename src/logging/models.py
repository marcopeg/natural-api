"""
Data models for logging system
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogEntry:
    """Complete log entry data structure"""
    
    timestamp: datetime
    status_code: int
    method: str
    path: str
    project_id: str
    user_id: str
    prompt_filename: str | None
    duration_ms: int
    command: str
    headers: dict[str, str]
    ai_output: str
    response_body: str
    cwd: str = ""
    error_context: str | None = None
