"""
Unit tests for request logging context
"""
import time
from unittest.mock import patch
from src.logging.context import RequestLogContext
from src.providers.base import AIProviderResult


def test_request_context_initialization():
    """Test context initialization"""
    ctx = RequestLogContext(
        method="GET",
        path="/test",
        project_id="default",
        user_id="anonymous",
        headers={"X-Project-Id": "default"}
    )
    
    assert ctx.method == "GET"
    assert ctx.path == "/test"
    assert ctx.project_id == "default"
    assert ctx.user_id == "anonymous"
    assert ctx.status_code == 500  # Default
    assert ctx.prompt_filename is None
    assert ctx.command == "none"


@patch('time.time', side_effect=[1000.0, 1001.5])
def test_request_context_duration(mock_time):
    """Test duration calculation"""
    ctx = RequestLogContext(
        method="GET",
        path="/test",
        project_id="default",
        user_id="anonymous",
        headers={}
    )
    
    duration = ctx.get_duration_ms()
    assert duration == 1500  # 1.5 seconds = 1500ms


def test_request_context_set_prompt():
    """Test setting prompt filename"""
    ctx = RequestLogContext("GET", "/test", "default", "anonymous", {})
    ctx.set_prompt("test.md")
    assert ctx.prompt_filename == "test.md"


def test_request_context_set_execution_result():
    """Test setting execution result"""
    ctx = RequestLogContext("GET", "/test", "default", "anonymous", {})
    
    result = AIProviderResult(
        stdout="output line 1",
        stderr="error line 1",
        returncode=0,
        success=True,
        command="codex exec 'test'"
    )
    
    ctx.set_execution_result(result)
    assert ctx.command == "codex exec 'test'"
    assert "output line 1" in ctx.ai_output
    assert "error line 1" in ctx.ai_output


def test_request_context_set_response():
    """Test setting response"""
    ctx = RequestLogContext("GET", "/test", "default", "anonymous", {})
    ctx.set_response("response body", 200)
    assert ctx.response_body == "response body"
    assert ctx.status_code == 200


def test_request_context_set_error():
    """Test setting error context"""
    ctx = RequestLogContext("GET", "/test", "default", "anonymous", {})
    ctx.set_error("timeout")
    assert ctx.error_context == "timeout"


def test_request_context_header_filtering():
    """Test that only specific headers are included in log entry"""
    ctx = RequestLogContext(
        method="GET",
        path="/test",
        project_id="default",
        user_id="anonymous",
        headers={
            "X-Project-Id": "test",
            "X-User-Id": "alice",
            "X-Dry": "true",
            "Authorization": "Bearer secret",  # Should be filtered
            "User-Agent": "curl/7.79.1",       # Should be filtered
            "Content-Type": "application/json" # Should be filtered
        }
    )
    
    entry = ctx.to_log_entry()
    
    assert "X-Project-Id" in entry.headers
    assert "X-User-Id" in entry.headers
    assert "X-Dry" in entry.headers
    assert "Authorization" not in entry.headers
    assert "User-Agent" not in entry.headers
    assert "Content-Type" not in entry.headers


def test_request_context_to_log_entry():
    """Test conversion to LogEntry"""
    ctx = RequestLogContext(
        method="GET",
        path="/test",
        project_id="default",
        user_id="anonymous",
        headers={"X-Project-Id": "default"}
    )
    
    ctx.set_prompt("test.md")
    ctx.set_response("response", 200)
    
    entry = ctx.to_log_entry()
    
    assert entry.method == "GET"
    assert entry.path == "/test"
    assert entry.project_id == "default"
    assert entry.user_id == "anonymous"
    assert entry.prompt_filename == "test.md"
    assert entry.status_code == 200
    assert entry.response_body == "response"
    assert entry.duration_ms >= 0
