from fastapi.testclient import TestClient
from src.main import app
from src.config import config
from unittest.mock import patch
from pathlib import Path

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "prompts"


def test_swagger_ui_served():
    if not config.OPENAPI_ENABLED:
        r = client.get("/openapi")
        assert r.status_code == 404
        return
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=FIXTURES_DIR):
            r = client.get("/openapi?project=test")
            assert r.status_code == 200
            assert "SwaggerUIBundle" in r.text
            assert "/openapi.json?project=test" in r.text


def test_swagger_ui_default_project():
    """Test Swagger UI with default project"""
    if not config.OPENAPI_ENABLED:
        return
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=FIXTURES_DIR):
            r = client.get("/openapi")
            assert r.status_code == 200
            assert "SwaggerUIBundle" in r.text
            assert "/openapi.json?project=default" in r.text


def test_swagger_ui_nonexistent_project():
    """Test Swagger UI with non-existent project"""
    if not config.OPENAPI_ENABLED:
        return
    with patch("src.config.config.project_exists", return_value=False):
        with patch("src.config.config.list_available_projects", return_value=["test", "default"]):
            r = client.get("/openapi?project=nonexistent")
            assert r.status_code == 404
            data = r.json()
            assert "available_projects" in data["detail"]
