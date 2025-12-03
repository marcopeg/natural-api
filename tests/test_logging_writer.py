"""
Unit tests for log writer
"""
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone
from pathlib import Path
import pytest
from src.logging.writer import write_log
from src.logging.models import LogEntry


def test_write_log_success():
    """Test successful log write"""
    with patch('src.logging.writer.config.get_log_file_path') as mock_get_path:
        mock_path = MagicMock(spec=Path)
        mock_get_path.return_value = mock_path
        
        entry = LogEntry(
            timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
            status_code=200,
            method="GET",
            path="/hi",
            project_id="default",
            user_id="anonymous",
            prompt_filename="hi.md",
            duration_ms=1000,
            command="codex exec 'hi'",
            headers={},
            ai_output="output",
            response_body="response",
            error_context=None
        )
        
        result = write_log(entry)
        
        assert result == mock_path
        mock_path.write_text.assert_called_once()
        # Check that write_text was called with encoding
        call_args = mock_path.write_text.call_args
        assert call_args[1]['encoding'] == 'utf-8'


def test_write_log_failure():
    """Test log write failure raises IOError"""
    with patch('src.logging.writer.config.get_log_file_path') as mock_get_path:
        mock_path = MagicMock(spec=Path)
        mock_path.write_text.side_effect = OSError("Disk full")
        mock_get_path.return_value = mock_path
        
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            status_code=200,
            method="GET",
            path="/test",
            project_id="default",
            user_id="anonymous",
            prompt_filename="test.md",
            duration_ms=100,
            command="test",
            headers={},
            ai_output="",
            response_body="",
            error_context=None
        )
        
        with pytest.raises(IOError, match="Failed to write log file"):
            write_log(entry)
