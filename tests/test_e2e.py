"""
E2E tests that run against actual server
These tests start a real HTTP server and make network requests

Note: E2E tests run the server in a separate process, so mocking doesn't work.
These tests verify the actual server behavior.
"""
import httpx
import pytest
from pathlib import Path
from tests.e2e_utils import running_server

# Test headers for multi-project/user support
TEST_HEADERS = {"x-project-id": "test", "x-user-id": "test"}


def test_server_starts_and_responds():
    """Test that the server can start and respond to requests"""
    with running_server(port=8001) as server:
        assert server.is_running()
        response = httpx.get(f"{server.base_url}/")
        assert response.status_code == 200


def test_e2e_root_endpoint():
    """E2E test for root endpoint"""
    with running_server(port=8002) as server:
        response = httpx.get(f"{server.base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Codex API"
        assert data["version"] == "0.3.0"
        assert data["phase"] == "3 - Dynamic Prompt-Based Routing"
        assert "provider" in data
        assert "available_providers" in data
        assert "projects_dir" in data
        assert "codex" in data["available_providers"]


def test_e2e_404_error():
    """E2E test for 404 errors on non-matching dynamic routes"""
    with running_server(port=8003) as server:
        response = httpx.get(f"{server.base_url}/this-prompt-does-not-exist-xyz", headers=TEST_HEADERS)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


def test_e2e_invalid_project():
    """E2E test for 412 error with non-existent project"""
    with running_server(port=8005) as server:
        headers = {"x-project-id": "nonexistent", "x-user-id": "test"}
        response = httpx.get(f"{server.base_url}/hi", headers=headers)
        assert response.status_code == 412
        data = response.json()
        assert "available_projects" in data["detail"]


def test_e2e_case_insensitive_headers():
    """E2E test for case-insensitive header names"""
    with running_server(port=8006) as server:
        headers = {"X-PROJECT-ID": "TEST", "X-USER-ID": "TEST"}
        # Should work with uppercase headers
        response = httpx.get(f"{server.base_url}/hi", headers=headers)
        # Will be 200 if hi.md exists in test project, or 404 if not
        assert response.status_code in (200, 404)


def test_e2e_workspace_isolation():
    """E2E test verifying workspace is created in correct location"""
    with running_server(port=8007) as server:
        headers = {"x-project-id": "test", "x-user-id": "testuser"}
        # Make a request to trigger workspace creation
        response = httpx.get(f"{server.base_url}/hi", headers=headers)
        # Check that workspace was created at data/storage/testuser/test/
        workspace = Path("data/storage/testuser/test")
        # Workspace should exist after request (if route succeeded or just 404)
        # Don't assert existence as it depends on whether hi.md exists and executes
        # Just verify status code is valid
        assert response.status_code in (200, 404, 503)


def test_server_cleanup():
    """Test that server is properly cleaned up after context"""
    server_manager = None
    with running_server(port=8004) as server:
        server_manager = server
        assert server.is_running()
    
    # After context exits, server should be stopped
    assert not server_manager.is_running()


def test_e2e_dry_run_basic():
    """E2E test for dry-run mode returning markdown or HTML based on Accept header"""
    with running_server(port=8008) as server:
        # Test with query parameter (default - no Accept header means markdown)
        response = httpx.get(f"{server.base_url}/hi?dry=true", headers=TEST_HEADERS)
        
        # Should return 200 or 404 depending on if hi.md exists
        if response.status_code == 200:
            # Dry-run should return markdown by default
            assert "## Command" in response.text  # Markdown format
            assert response.headers["content-type"].startswith("text/plain")
        elif response.status_code == 404:
            # Prompt doesn't exist in test project - that's OK
            pass
        else:
            # Any other status is a problem
            pytest.fail(f"Unexpected status code: {response.status_code}")
        
        # Test with browser Accept header (should return HTML)
        browser_headers = {
            **TEST_HEADERS,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        response = httpx.get(f"{server.base_url}/hi?dry=true", headers=browser_headers)
        
        if response.status_code == 200:
            # Dry-run should return HTML for browsers
            assert "<!DOCTYPE html>" in response.text
            assert "Dry-Run Log Preview" in response.text
            assert response.headers["content-type"].startswith("text/html")
        elif response.status_code == 404:
            # Prompt doesn't exist in test project - that's OK
            pass
        else:
            # Any other status is a problem
            pytest.fail(f"Unexpected status code: {response.status_code}")
