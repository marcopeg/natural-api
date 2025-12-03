import json
from pathlib import Path

from src.openapi.generator import generate_openapi
from src.config import config


def test_generate_openapi_success(tmp_path: Path):
    # Use existing fixtures directory
    prompts_dir = Path(__file__).parent / "fixtures" / "prompts"
    doc = generate_openapi(prompts_dir)
    assert "openapi" in doc
    assert "paths" in doc
    # Should include some known paths from fixtures
    paths = doc["paths"]
    assert "/greet/{name}" in paths


def test_generate_openapi_conflict_detection(tmp_path: Path):
    # Create a temp prompts dir with conflicting routes
    pdir = tmp_path / "prompts"
    pdir.mkdir(parents=True, exist_ok=True)

    # Two files with same explicit route
    (pdir / "a.md").write_text("""---
route: /same
method: GET
---
Hello A
""", encoding="utf-8")
    (pdir / "b.md").write_text("""---
route: /same
method: GET
---
Hello B
""", encoding="utf-8")

    result = generate_openapi(pdir)
    assert "errors" in result
    assert any(e["type"] == "route_conflict" for e in result["errors"])