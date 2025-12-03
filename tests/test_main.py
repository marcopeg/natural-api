"""
Tests for main API endpoints
"""
from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch
from src.providers.base import AIProviderResult
from src.prompts.router import RouteMatch
from src.prompts.loader import PromptMetadata
from pathlib import Path

client = TestClient(app)

# Test headers for multi-project/user support
TEST_HEADERS = {"x-project-id": "test", "x-user-id": "test"}


def test_root_endpoint():
    """Test the root endpoint returns API information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Codex API"
    assert data["version"] == "0.3.0"
    assert data["phase"] == "3 - Dynamic Prompt-Based Routing"
    assert "provider" in data
    assert "available_providers" in data
    assert "projects_dir" in data


# Dynamic route tests


def test_dynamic_route_success():
    """Test dynamic route with successful execution"""
    mock_result = AIProviderResult(
        stdout="Hello from AI",
        stderr="",
        returncode=0,
        success=True,
        error_message=None,
        command="test command"
    )
    
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Test prompt"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                            response = client.get("/test", headers=TEST_HEADERS)
                            assert response.status_code == 200
                            assert response.text == "Hello from AI"


def test_dynamic_route_404():
    """Test dynamic route with no matching prompt"""
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=None):
                        response = client.get("/no-such-route", headers=TEST_HEADERS)
                        assert response.status_code == 404
                        data = response.json()
                        assert "detail" in data


def test_dynamic_route_explicit_match():
    """Test dynamic route with explicit route match"""
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test/{id}",
        model=None,
        agent=None,
        raw_content="Test ${id}"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="explicit",
        path_params={"id": "123"}
    )
    
    mock_result = AIProviderResult(
        stdout="Test result",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                response = client.get("/test/123", headers=TEST_HEADERS)
                                assert response.status_code == 200
                                assert response.text == "Test result"


def test_dynamic_route_provider_unavailable():
    """Test dynamic route when provider is unavailable"""
    from src.prompts.router import RouteMatch
    from src.prompts.loader import PromptMetadata
    from pathlib import Path
    
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        verb="GET",
        route="/test",
        model=None,
        agent=None,
        raw_content="Test"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="explicit",
        path_params={}
    )
    
    with patch("src.prompts.router.DynamicRouter.load_prompts"):
        with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
            with patch("src.providers.codex.CodexProvider.is_available", return_value=False):
                response = client.get("/test")
                assert response.status_code == 503


            with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                    response = client.get("/test/123")
                    assert response.status_code == 200
                    assert response.text == "Test result"


def test_dynamic_route_provider_unavailable():
    """Test dynamic route when provider is unavailable"""
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model=None,
        agent=None,
        raw_content="Test"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="explicit",
        path_params={}
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=False):
                            response = client.get("/test", headers=TEST_HEADERS)
                            assert response.status_code == 503


def test_dynamic_route_timeout():
    """Test dynamic route when AI execution times out"""
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model=None,
        agent=None,
        raw_content="Test"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="explicit",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="",
        stderr="timeout",
        returncode=124,
        success=False,
        error_message="Timeout",
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                response = client.get("/test", headers=TEST_HEADERS)
                                assert response.status_code == 408


def test_dynamic_route_execution_failure():
    """Test dynamic route when AI execution fails"""
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model=None,
        agent=None,
        raw_content="Test"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="explicit",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="",
        stderr="error",
        returncode=1,
        success=False,
        error_message="Execution failed",
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                response = client.get("/test", headers=TEST_HEADERS)
                                assert response.status_code == 500


# Multi-project/user tests

def test_dynamic_route_invalid_project():
    """Test 412 error for non-existent project"""
    headers = {"x-project-id": "nonexistent", "x-user-id": "test"}
    with patch("src.config.config.project_exists", return_value=False):
        with patch("src.config.config.list_available_projects", return_value=["test", "default"]):
            response = client.get("/test", headers=headers)
            assert response.status_code == 412
            data = response.json()
            assert "available_projects" in data["detail"]


def test_dynamic_route_invalid_project_format():
    """Test 400 error for invalid project ID format"""
    headers = {"x-project-id": "invalid@project", "x-user-id": "test"}
    response = client.get("/test", headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert "must match [a-zA-Z0-9-]+" in data["detail"]["message"]


def test_dynamic_route_case_insensitive_headers():
    """Test case-insensitive header names"""
    headers = {"X-PROJECT-ID": "TEST", "X-USER-ID": "TEST"}
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model=None,
        agent=None,
        raw_content="Test"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="Success",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                response = client.get("/test", headers=headers)
                                assert response.status_code == 200


def test_dynamic_route_default_project_user():
    """Test that requests work without headers (default project/user)"""
    mock_prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model=None,
        agent=None,
        raw_content="Test"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="Success",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/default/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                # No headers - should default to "default" and "anonymous"
                                response = client.get("/test")
                                assert response.status_code == 200


# Dry-run mode tests


def test_dry_run_via_query_parameter():
    """Test dry-run mode via query parameter"""
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Say hello",
        dry=None
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="codex exec --sandbox workspace-write --model gpt-5.1-codex-mini 'Say hello'",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result) as mock_exec:
                                # Default (curl/API): returns markdown
                                response = client.get("/hi?dry=true", headers=TEST_HEADERS)
                                assert response.status_code == 200
                                assert response.headers["content-type"] == "text/plain; charset=utf-8"
                                assert "test command" in response.text
                                assert "## Command" in response.text  # Markdown format
                                # Verify dry_run was passed
                                mock_exec.assert_called_once()
                                call_kwargs = mock_exec.call_args[1]
                                assert call_kwargs["dry_run"] is True


def test_dry_run_via_header():
    """Test dry-run mode via x-dry header"""
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Say hello",
        dry=None
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="codex exec --sandbox workspace-write --model gpt-5.1-codex-mini 'Say hello'",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    headers = {**TEST_HEADERS, "x-dry": "true"}
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result) as mock_exec:
                                # Default (curl/API): returns markdown
                                response = client.get("/hi", headers=headers)
                                assert response.status_code == 200
                                assert response.headers["content-type"] == "text/plain; charset=utf-8"
                                assert "test command" in response.text
                                assert "## Command" in response.text  # Markdown format
                                # Verify dry_run was passed
                                call_kwargs = mock_exec.call_args[1]
                                assert call_kwargs["dry_run"] is True


def test_dry_run_disabled_via_query():
    """Test dry-run disabled with ?dry=false"""
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Say hello",
        dry=None
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="Hello!",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result) as mock_exec:
                                response = client.get("/hi?dry=false", headers=TEST_HEADERS)
                                assert response.status_code == 200
                                # Verify dry_run was False
                                call_kwargs = mock_exec.call_args[1]
                                assert call_kwargs["dry_run"] is False


def test_dry_run_precedence_prompt_over_header():
    """Test that prompt-level dry wins over header"""
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Say hello",
        dry=True  # Prompt-level dry=true
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="codex exec --sandbox workspace-write --model gpt-5.1-codex-mini 'Say hello'",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    headers = {**TEST_HEADERS, "x-dry": "false"}  # Header says false
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result) as mock_exec:
                                response = client.get("/hi?dry=false", headers=headers)
                                assert response.status_code == 200
                                # Prompt wins - should be True
                                call_kwargs = mock_exec.call_args[1]
                                assert call_kwargs["dry_run"] is True


def test_dry_run_precedence_header_over_query():
    """Test that header dry wins over query parameter"""
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Say hello",
        dry=None  # No prompt-level dry
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="codex exec --sandbox workspace-write --model gpt-5.1-codex-mini 'Say hello'",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    headers = {**TEST_HEADERS, "x-dry": "true"}  # Header says true
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result) as mock_exec:
                                response = client.get("/hi?dry=false", headers=headers)  # Query says false
                                assert response.status_code == 200
                                # Header wins - should be True
                                call_kwargs = mock_exec.call_args[1]
                                assert call_kwargs["dry_run"] is True


def test_dry_run_response_html_for_browsers():
    """Test that dry-run returns HTML when client sends Accept: text/html"""
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Say hello",
        dry=None
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="codex exec --sandbox workspace-write --model gpt-5.1-codex-mini 'Say hello'",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                # Browser client: sends Accept: text/html
                                browser_headers = {**TEST_HEADERS, "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
                                response = client.get("/hi?dry=true", headers=browser_headers)
                                assert response.status_code == 200
                                assert response.headers["content-type"] == "text/html; charset=utf-8"
                                assert "<!DOCTYPE html>" in response.text
                                assert "Dry-Run Log Preview" in response.text


def test_dry_run_response_markdown_for_cli():
    """Test that dry-run returns markdown when client doesn't request HTML"""
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        raw_content="Say hello",
        dry=None
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="codex exec --sandbox workspace-write --model gpt-5.1-codex-mini 'Say hello'",
        stderr="",
        returncode=0,
        success=True,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                # CLI client: sends Accept: */* or text/plain
                                cli_headers = {**TEST_HEADERS, "accept": "*/*"}
                                response = client.get("/hi?dry=true", headers=cli_headers)
                                assert response.status_code == 200
                                assert response.headers["content-type"] == "text/plain; charset=utf-8"
                                assert "## Command" in response.text  # Markdown
                                assert "test command" in response.text
                                assert "<!DOCTYPE html>" not in response.text  # Not HTML


def test_hidden_resources_blocked():
    """Test that standard browser/infrastructure paths are blocked"""
    # Test favicon
    response = client.get("/favicon.ico")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "Not Found"
    assert "Resource not available" in data["detail"]["message"]
    
    # Test robots.txt
    response = client.get("/robots.txt")
    assert response.status_code == 404
    
    # Test .well-known path
    response = client.get("/.well-known/test")
    assert response.status_code == 404
    
    # Test .git path
    response = client.get("/.git/config")
    assert response.status_code == 404
    
    # Test nested .well-known
    response = client.get("/.well-known/security.txt")
    assert response.status_code == 404
    
    # Test apple touch icon
    response = client.get("/apple-touch-icon.png")
    assert response.status_code == 404
    
    # Test .vscode
    response = client.get("/.vscode/settings.json")
    assert response.status_code == 404
    
    # Test normal path still works (with mocking)
    mock_prompt = PromptMetadata(
        filename="hi",
        filepath=Path("/tmp/hi.md"),
        method="GET",
        route=None,
        model=None,
        agent=None,
        body_schema=None,
        dry=None,
        raw_content="Test"
    )
    
    mock_match = RouteMatch(
        prompt=mock_prompt,
        match_type="fallback",
        path_params={}
    )
    
    mock_result = AIProviderResult(
        stdout="Hello",
        stderr="",
        returncode=0,
        success=True,
        error_message=None,
        command="test command"
    )
    
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.providers.codex.CodexProvider.is_available", return_value=True):
                            with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                                response = client.get("/hi", headers=TEST_HEADERS)
                                assert response.status_code == 200



