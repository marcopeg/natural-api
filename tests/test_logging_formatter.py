"""
Unit tests for log formatter
"""
import json
from datetime import datetime, timezone
from src.logging.models import LogEntry
from src.logging.formatter import format_log_markdown


def test_format_log_markdown_basic_structure():
    """Test that log markdown has all required sections"""
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=200,
        method="GET",
        path="/hi",
        project_id="default",
        user_id="anonymous",
        prompt_filename="hi.md",
        duration_ms=1000,
        command="codex exec 'prompt'",
        headers={"X-Project-Id": "default", "X-User-Id": "anonymous"},
        ai_output="Hello!",
        response_body="Hello!",
        error_context=None
    )
    
    markdown = format_log_markdown(entry)
    
    # Check title
    assert "# 2025/12/03 14:15:30.123456 UTC" in markdown
    
    # Check metadata table - numeric timestamp instead of human-readable
    assert "| Timestamp | 20251203-141530.123456" in markdown
    assert "| Status    | 200" in markdown
    assert "| Method    | GET" in markdown
    assert "| Path      | /hi" in markdown
    assert "| Project   | default" in markdown
    assert "| User      | anonymous" in markdown
    assert "| Prompt    | hi.md" in markdown
    assert "| Duration  | 1000ms" in markdown
    
    # Check table alignment (26 char width for values)
    assert "| Key       | Value                      |" in markdown
    assert "|-----------|----------------------------|" in markdown
    
    # Check sections
    assert "## Command" in markdown
    assert "```bash" in markdown
    assert "codex exec 'prompt'" in markdown
    assert "## Headers" in markdown
    assert "## AI Output" in markdown
    assert "## Response" in markdown


def test_format_log_markdown_with_error_context():
    """Test duration field includes error context"""
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=408,
        method="GET",
        path="/slow",
        project_id="default",
        user_id="anonymous",
        prompt_filename="slow.md",
        duration_ms=5000,
        command="codex exec 'slow command'",
        headers={},
        ai_output="Partial output",
        response_body='{"error": "timeout"}',
        error_context="timeout"
    )
    
    markdown = format_log_markdown(entry)
    assert "| Duration  | 5000ms (timeout)" in markdown


def test_format_log_markdown_no_prompt():
    """Test with no prompt (404 scenario)"""
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=404,
        method="GET",
        path="/nonexistent",
        project_id="default",
        user_id="anonymous",
        prompt_filename=None,
        duration_ms=10,
        command="none",
        headers={},
        ai_output="",
        response_body='{"error": "Not Found"}',
        error_context=None
    )
    
    markdown = format_log_markdown(entry)
    assert "| Prompt    | not-found" in markdown


def test_format_log_markdown_headers_filtering():
    """Test that only specific headers are included"""
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=200,
        method="GET",
        path="/test",
        project_id="test",
        user_id="alice",
        prompt_filename="test.md",
        duration_ms=100,
        command="test command",
        headers={
            "X-Project-Id": "test",
            "X-User-Id": "alice",
            "X-Dry": "true"
        },
        ai_output="output",
        response_body="response",
        error_context=None
    )
    
    markdown = format_log_markdown(entry)
    assert "X-Project-Id" in markdown
    assert "X-User-Id" in markdown
    assert "X-Dry" in markdown


def test_format_log_markdown_json_response():
    """Test that JSON responses are formatted"""
    response_dict = {"status": "success", "data": {"value": 42}}
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=200,
        method="GET",
        path="/api",
        project_id="default",
        user_id="anonymous",
        prompt_filename="api.md",
        duration_ms=200,
        command="command",
        headers={},
        ai_output="output",
        response_body=json.dumps(response_dict),
        error_context=None
    )
    
    markdown = format_log_markdown(entry)
    assert "```json" in markdown
    assert '"status": "success"' in markdown
    assert '"value": 42' in markdown


def test_format_log_markdown_text_response():
    """Test plain text response"""
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=200,
        method="GET",
        path="/text",
        project_id="default",
        user_id="anonymous",
        prompt_filename="text.md",
        duration_ms=150,
        command="command",
        headers={},
        ai_output="output",
        response_body="Plain text response",
        error_context=None
    )
    
    markdown = format_log_markdown(entry)
    assert "```text" in markdown
    assert "Plain text response" in markdown


def test_format_log_markdown_empty_ai_output():
    """Test with empty AI output"""
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=404,
        method="GET",
        path="/test",
        project_id="default",
        user_id="anonymous",
        prompt_filename=None,
        duration_ms=10,
        command="none",
        headers={},
        ai_output="",
        response_body="{}",
        error_context=None
    )
    
    markdown = format_log_markdown(entry)
    assert "No execution" in markdown


def test_format_log_markdown_dry_run_omits_sections():
    """Test that dry-run mode omits AI Output and Response sections"""
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=200,
        method="GET",
        path="/hi",
        project_id="default",
        user_id="anonymous",
        prompt_filename="hi.md",
        duration_ms=100,
        command="codex exec 'Test prompt'",
        headers={"X-Dry": "true"},
        ai_output="Not executed (dry-run mode)",
        response_body="Dry-run - no AI execution",
        error_context=None
    )
    
    # Regular mode includes both sections
    markdown_regular = format_log_markdown(entry, is_dry_run=False)
    assert "## AI Output" in markdown_regular
    assert "## Response" in markdown_regular
    
    # Dry-run mode omits both sections
    markdown_dry = format_log_markdown(entry, is_dry_run=True)
    assert "## AI Output" not in markdown_dry
    assert "## Response" not in markdown_dry
    
    # But still includes other sections
    assert "## Command" in markdown_dry
    assert "## Headers" in markdown_dry
    assert "| Timestamp |" in markdown_dry
