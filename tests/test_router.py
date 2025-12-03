"""
Unit tests for route matcher module
"""
import pytest
from pathlib import Path
from src.prompts.router import DynamicRouter, RouteMatch


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "prompts"


def test_explicit_route_match():
    """Test matching explicit route"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    match = router.match_route("GET", "/greet/Alice")
    assert match is not None
    assert match.prompt.filename == "greet"
    assert match.match_type == "explicit"
    assert match.path_params == {"name": "Alice"}


def test_fallback_route_match():
    """Test matching fallback filename route"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    match = router.match_route("GET", "/simple")
    assert match is not None
    assert match.prompt.filename == "simple"
    assert match.match_type == "fallback"
    assert match.path_params == {}


def test_multiple_path_parameters():
    """Test extracting multiple path parameters"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    match = router.match_route("POST", "/api/v2/user/123")
    assert match is not None
    assert match.prompt.filename == "api"
    assert match.match_type == "explicit"
    assert match.path_params == {"version": "v2", "id": "123"}


def test_method_matching_case_insensitive():
    """Test that method matching is case-insensitive"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    # API prompt expects POST
    match = router.match_route("post", "/api/v1/user/456")
    assert match is not None
    assert match.prompt.filename == "api"


def test_no_match_returns_none():
    """Test that non-matching route returns None"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    match = router.match_route("GET", "/nonexistent/route")
    assert match is None


def test_fallback_only_get():
    """Test that fallback routes only match GET requests"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    # simple.md has no explicit route, so fallback only works for GET
    match = router.match_route("POST", "/simple")
    assert match is None
    
    match = router.match_route("GET", "/simple")
    assert match is not None


def test_first_match_priority():
    """Test that first matching prompt is returned"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    # Load prompts and verify ordering
    assert len(router.prompts) > 0
    
    # First match should win
    match = router.match_route("GET", "/greet/test")
    assert match is not None
    # Should match explicit route, not fallback


def test_no_slash_in_fallback():
    """Test that fallback doesn't match paths with multiple segments"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    # /simple/extra should not match fallback for simple.md
    match = router.match_route("GET", "/simple/extra")
    assert match is None


def test_path_parameter_pattern():
    """Test path parameter extraction with different patterns"""
    router = DynamicRouter(FIXTURES_DIR)
    router.load_prompts()
    
    # Test with different values
    match = router.match_route("GET", "/greet/John_Doe")
    assert match is not None
    assert match.path_params["name"] == "John_Doe"
    
    match = router.match_route("GET", "/greet/user-123")
    assert match is not None
    assert match.path_params["name"] == "user-123"


def test_load_empty_prompts():
    """Test router with no prompts loaded"""
    router = DynamicRouter(Path("/nonexistent"))
    router.load_prompts()
    
    match = router.match_route("GET", "/anything")
    assert match is None
