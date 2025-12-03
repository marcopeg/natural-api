"""
Markdown log formatter
"""
import json
from src.logging.models import LogEntry
from src.logging.timestamp import format_title_timestamp, format_numeric_timestamp


def format_log_markdown(entry: LogEntry, is_dry_run: bool = False) -> str:
    """
    Format log entry as markdown document.
    
    Args:
        entry: LogEntry to format
        is_dry_run: If True, omit AI Output and Response sections
        
    Returns:
        str: Complete markdown document
    """
    sections = [
        f"# {format_title_timestamp(entry.timestamp)}",
        "",
        _format_metadata_table(entry),
        "",
        _format_command_section(entry.command),
        "",
        _format_headers_table(entry.headers),
    ]
    
    # Only include AI Output and Response sections if not dry-run
    if not is_dry_run:
        sections.extend([
            "",
            _format_ai_output_section(entry.ai_output),
            "",
            _format_response_section(entry.response_body, entry.status_code),
        ])
    
    return "\n".join(sections)


def _format_metadata_table(entry: LogEntry) -> str:
    """Format metadata table section with compact, aligned columns"""
    duration_str = f"{entry.duration_ms}ms"
    if entry.error_context:
        duration_str += f" ({entry.error_context})"
    
    prompt_name = entry.prompt_filename if entry.prompt_filename else "not-found"
    timestamp_numeric = format_numeric_timestamp(entry.timestamp)
    request_id_value = entry.request_id if entry.request_id else "none"
    
    lines = [
        "| Key        | Value                      |",
        "|------------|----------------------------|",
        f"| Request ID | {request_id_value:<26} |",
        f"| Timestamp  | {timestamp_numeric:<26} |",
        f"| Status     | {entry.status_code:<26} |",
        f"| Method     | {entry.method:<26} |",
        f"| Path       | {entry.path:<26} |",
        f"| Project    | {entry.project_id:<26} |",
        f"| User       | {entry.user_id:<26} |",
        f"| Prompt     | {prompt_name:<26} |",
        f"| CWD        | {entry.cwd:<26} |",
        f"| Duration   | {duration_str:<26} |",
    ]
    return "\n".join(lines)


def _format_command_section(command: str) -> str:
    """Format command section"""
    return f"## Command\n\n```bash\n{command}\n```"


def _format_headers_table(headers: dict[str, str]) -> str:
    """Format headers table (only X-Project-Id, X-User-Id, X-Dry)"""
    lines = [
        "## Headers",
        "",
        "| Key           | Value                     |",
        "|---------------|---------------------------|",
    ]
    
    # Only include specific headers
    for key in ["X-Project-Id", "X-User-Id", "X-Dry"]:
        value = headers.get(key, headers.get(key.lower(), ""))
        lines.append(f"| {key:<13} | {value:<25} |")
    
    return "\n".join(lines)


def _format_ai_output_section(ai_output: str) -> str:
    """Format AI output section"""
    content = ai_output if ai_output else "No execution"
    return f"## AI Output\n\n```text\n{content}\n```"


def _format_response_section(response_body: str, status_code: int) -> str:
    """Format response section"""
    # Try to parse as JSON for pretty formatting
    try:
        parsed = json.loads(response_body)
        formatted = json.dumps(parsed, indent=2)
        return f"## Response\n\n```json\n{formatted}\n```"
    except (json.JSONDecodeError, TypeError):
        # Not JSON, treat as text
        # Truncate if too long (> 10KB)
        max_length = 10240
        if len(response_body) > max_length:
            truncated = response_body[:max_length]
            return f"## Response\n\n```text\n{truncated}\n\n... (truncated, {len(response_body)} bytes total)\n```"
        else:
            return f"## Response\n\n```text\n{response_body}\n```"
