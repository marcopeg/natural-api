"""
Unit tests for prompt loader module
"""
import pytest
from pathlib import Path
from src.prompts.loader import load_prompts, PromptMetadata


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "prompts"


def test_load_valid_prompts():
    """Test loading prompts with valid frontmatter"""
    prompts = load_prompts(FIXTURES_DIR)
    
    # Should load at least the valid ones
    assert len(prompts) >= 3
    
    # Check greet.md
    greet = next((p for p in prompts if p.filename == "greet"), None)
    assert greet is not None
    assert greet.route == "/greet/{name}"
    assert greet.method == "GET"
    assert greet.model == "gpt-5.1-codex-mini"
    assert greet.agent is None
    assert "${name}" in greet.raw_content


def test_load_minimal_prompt():
    """Test loading prompt without frontmatter"""
    prompts = load_prompts(FIXTURES_DIR)
    
    minimal = next((p for p in prompts if p.filename == "minimal"), None)
    assert minimal is not None
    assert minimal.method == "GET"  # default
    assert minimal.route is None  # no explicit route
    assert minimal.model is None
    assert minimal.agent is None
    assert "minimal prompt" in minimal.raw_content


def test_load_prompt_with_multiple_params():
    """Test loading prompt with multiple path parameters"""
    prompts = load_prompts(FIXTURES_DIR)
    
    api = next((p for p in prompts if p.filename == "api"), None)
    assert api is not None
    assert api.route == "/api/{version}/user/{id}"
    assert api.method == "POST"
    assert "${version}" in api.raw_content
    assert "${id}" in api.raw_content


def test_load_invalid_yaml_graceful():
    """Test that invalid YAML files are handled gracefully"""
    prompts = load_prompts(FIXTURES_DIR)
    
    # Invalid file should be skipped
    invalid = next((p for p in prompts if p.filename == "invalid"), None)
    # Either skipped or loaded with empty metadata
    if invalid is not None:
        # If loaded, should have defaults
        assert invalid.method == "GET"


def test_load_empty_directory():
    """Test loading from empty directory"""
    empty_dir = Path(__file__).parent / "empty_prompts"
    empty_dir.mkdir(exist_ok=True)
    
    prompts = load_prompts(empty_dir)
    assert len(prompts) == 0
    
    # Cleanup
    empty_dir.rmdir()


def test_load_nonexistent_directory():
    """Test loading from non-existent directory"""
    nonexistent = Path("/nonexistent/path")
    prompts = load_prompts(nonexistent)
    assert len(prompts) == 0


def test_filename_extraction():
    """Test that filenames are extracted correctly without .md extension"""
    prompts = load_prompts(FIXTURES_DIR)
    
    for prompt in prompts:
        assert not prompt.filename.endswith(".md")
        assert prompt.filepath.suffix == ".md"
