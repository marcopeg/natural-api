"""
Request logging context manager
"""
import time
from src.logging.models import LogEntry
from src.logging.timestamp import generate_timestamp
from src.providers.base import AIProviderResult


class RequestLogContext:
    """
    Manages logging state throughout request lifecycle.
    Tracks all data needed for final log entry.
    """
    
    def __init__(self, method: str, path: str, project_id: str, user_id: str, headers: dict):
        """
        Initialize logging context.
        
        Args:
            method: HTTP method
            path: Request path
            project_id: Project ID (resolved)
            user_id: User ID (resolved)
            headers: Request headers dict
        """
        self.timestamp = generate_timestamp()
        self.start_time = time.time()
        self.method = method
        self.path = path
        self.project_id = project_id
        self.user_id = user_id
        self.headers = headers
        
        # Updated during request processing
        self.prompt_filename: str | None = None
        self.command: str = "none"
        self.ai_output: str = ""
        self.response_body: str = ""
        self.status_code: int = 500  # Default to error
        self.error_context: str | None = None
        self.cwd: str = ""
    
    def set_prompt(self, filename: str):
        """Set prompt filename"""
        self.prompt_filename = filename
    
    def set_execution_result(self, result: AIProviderResult):
        """Update context with AI execution result"""
        self.command = result.command
        # Combine stdout and stderr for AI output
        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(result.stderr)
        self.ai_output = "\n".join(output_parts).strip()
    
    def set_response(self, body: str, status: int):
        """Set response body and status code"""
        self.response_body = body
        self.status_code = status
    
    def set_error(self, context: str):
        """Set error context (e.g., 'timeout', 'execution_failed')"""
        self.error_context = context

    def set_cwd(self, cwd: str):
        """Set current working directory used for provider execution"""
        self.cwd = cwd
    
    def get_duration_ms(self) -> int:
        """Calculate duration in milliseconds"""
        return int((time.time() - self.start_time) * 1000)
    
    def to_log_entry(self) -> LogEntry:
        """
        Convert context to LogEntry.
        
        Returns:
            LogEntry: Complete log entry ready for formatting/writing
        """
        # Filter headers to only X-Project-Id, X-User-Id, X-Dry
        filtered_headers = {}
        for key, value in self.headers.items():
            key_lower = key.lower()
            if key_lower in ['x-project-id', 'x-user-id', 'x-dry']:
                # Store with original key for display
                filtered_headers[key] = value
        
        return LogEntry(
            timestamp=self.timestamp,
            status_code=self.status_code,
            method=self.method,
            path=self.path,
            project_id=self.project_id,
            user_id=self.user_id,
            prompt_filename=self.prompt_filename,
            duration_ms=self.get_duration_ms(),
            cwd=self.cwd,
            command=self.command,
            headers=filtered_headers,
            ai_output=self.ai_output,
            response_body=self.response_body,
            error_context=self.error_context
        )
