"""
Unit tests for HTML formatter
"""
from src.logging.html_formatter import format_log_html


def test_format_log_html_structure():
    """Test HTML document structure"""
    markdown = "# Test Log\n\nSome content"
    html = format_log_html(markdown)
    
    assert "<!DOCTYPE html>" in html
    assert "<html>" in html
    assert "<head>" in html
    assert "<title>Dry-Run Log Preview</title>" in html
    assert "<style>" in html
    assert "<body>" in html
    assert "</body>" in html
    assert "</html>" in html


def test_format_log_html_escapes_content():
    """Test that markdown is rendered to HTML, not escaped"""
    markdown = "**bold** and `code`"
    html = format_log_html(markdown)
    
    # Markdown should be converted to HTML
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    
    # HTML that's already in markdown should be passed through by markdown library
    # (Note: markdown library sanitizes dangerous HTML by default)


def test_format_log_html_includes_markdown():
    """Test that markdown content is included"""
    markdown = "# My Log\n\n| Key | Value |\n|-----|-------|\n| Status | 200 |"
    html = format_log_html(markdown)
    
    # Markdown should be in the body (escaped)
    assert "My Log" in html
    assert "Status" in html
