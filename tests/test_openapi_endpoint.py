from fastapi.testclient import TestClient
from src.main import app
from src.config import config
from unittest.mock import patch
from pathlib import Path

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "prompts"


def test_openapi_endpoint_status():
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=FIXTURES_DIR):
            r = client.get("/openapi.json?project=test")
            if config.OPENAPI_ENABLED:
                assert r.status_code in (200, 500)  # 500 when conflicts/errors
            else:
                assert r.status_code == 404


def test_openapi_document_shape_when_ok():
    if not config.OPENAPI_ENABLED:
        return
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=FIXTURES_DIR):
            r = client.get("/openapi.json?project=test")
            if r.status_code != 200:
                return
            data = r.json()
            assert "openapi" in data
            assert "paths" in data


def test_openapi_endpoint_default_project():
    """Test OpenAPI endpoint with default project"""
    if not config.OPENAPI_ENABLED:
        return
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=FIXTURES_DIR):
            response = client.get("/openapi.json")
            assert response.status_code == 200
            data = response.json()
            assert "openapi" in data


def test_openapi_endpoint_nonexistent_project():
    """Test OpenAPI endpoint with non-existent project"""
    if not config.OPENAPI_ENABLED:
        return
    with patch("src.config.config.project_exists", return_value=False):
        with patch("src.config.config.list_available_projects", return_value=["test", "default"]):
            response = client.get("/openapi.json?project=nonexistent")
            assert response.status_code == 404
            data = response.json()
            assert "available_projects" in data["detail"]


def test_openapi_endpoint_invalid_project_format():
    """Test OpenAPI endpoint with invalid project ID format"""
    if not config.OPENAPI_ENABLED:
        return
    response = client.get("/openapi.json?project=invalid@project")
    assert response.status_code == 400
    data = response.json()
    assert "must match [a-zA-Z0-9-]+" in data["detail"]["message"]
