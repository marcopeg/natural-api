# Implementation Plan for Task 008

Multi-Project and Multi-User Support

**STATUS: ✅ COMPLETED**
**Date Completed: December 3, 2025**
**Tests Passing: 132/132**

---

## Codebase Analysis Summary

### Current State
- **Config**: `config.get_prompts_dir()` returns `./data/prompts` (hardcoded path)
- **Main Handler**: Uses `config.get_prompts_dir()` to load prompts (line 126)
- **OpenAPI**: Uses `config.get_prompts_dir()` to generate docs (line 68)
- **DynamicRouter**: Takes `prompts_dir` as constructor parameter
- **PromptExecutor**: Takes `workspace_dir` as constructor parameter
- **Tests**: Use `FIXTURES_DIR` pointing to `tests/fixtures/prompts/`
- **Data Migration**: Test prompts already in `/data/projects/test/prompts/`

### Key Touchpoints
1. `src/config.py` - Add project/storage directories and helper methods
2. `src/main.py` - Extract headers, validate projects, setup workspaces
3. All test files - Add headers `x-project-id: test` and `x-user-id: test`
4. Test fixtures - Already migrated to `data/projects/test/prompts/`

### Critical Dependencies
- `DynamicRouter` and `generate_openapi()` already accept `prompts_dir` parameter ✅
- `PromptExecutor` already accepts `workspace_dir` parameter ✅
- No changes needed to loader, router, or executor modules ✅
- Main work is in config, main.py, and tests

---

## Phase 1: Core Infrastructure ✅

### Task 1.1: Add Config Methods for Multi-Project Support ✅
**File**: `src/config.py`

**Estimated Time**: 30 minutes

**Current Code**:
```python
PROMPTS_DIR: Path = WORKSPACE_DIR / "prompts"

@classmethod
def get_prompts_dir(cls) -> Path:
    prompts_dir = cls.WORKSPACE_DIR / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    return prompts_dir
```

**Changes**:
```python
# Add new class variables
PROJECTS_DIR: Path = WORKSPACE_DIR / "projects"
STORAGE_DIR: Path = WORKSPACE_DIR / "storage"

# Add new methods
@classmethod
def get_projects_dir(cls) -> Path:
    """Get projects base directory"""
    return cls.PROJECTS_DIR

@classmethod
def get_storage_dir(cls) -> Path:
    """Get storage base directory"""
    return cls.STORAGE_DIR

@classmethod
def get_project_dir(cls, project_id: str) -> Path:
    """Get project directory (not creating it)"""
    return cls.PROJECTS_DIR / project_id.lower()

@classmethod
def get_project_prompts_dir(cls, project_id: str) -> Path:
    """Get project's prompts directory"""
    return cls.get_project_dir(project_id) / "prompts"

@classmethod
def get_user_workspace_dir(cls, user_id: str, project_id: str) -> Path:
    """Get user's workspace directory for a specific project"""
    return cls.STORAGE_DIR / user_id.lower() / project_id.lower()

@classmethod
def list_available_projects(cls) -> list[str]:
    """List all available projects"""
    if not cls.PROJECTS_DIR.exists():
        return []
    return sorted([d.name for d in cls.PROJECTS_DIR.iterdir() if d.is_dir()])

@classmethod
def project_exists(cls, project_id: str) -> bool:
    """Check if project directory exists"""
    return cls.get_project_dir(project_id).exists()
```

**Keep Backward Compatibility**:
- Keep `get_prompts_dir()` for now (will be deprecated in Phase 5)
- Keep `PROMPTS_DIR` for now (will be removed in Phase 5)

**Tests**: Create `tests/test_config.py`
```python
def test_get_project_dir()
def test_get_project_prompts_dir()
def test_get_user_workspace_dir()
def test_list_available_projects()
def test_project_exists()
def test_case_insensitive_paths()
```

**Validation**: Run `pytest tests/test_config.py -v`

---

### Task 1.2: Add Header Extraction & Validation Helpers
**File**: `src/main.py` (add before route handlers)

**Estimated Time**: 45 minutes

**Changes**:
Add these helper functions at module level (after imports, before app creation):

```python
import re

# Regex for validating project/user IDs
PROJECT_USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+$')

def extract_header(request: Request, name: str, default: str) -> str:
    """
    Extract header value with case-insensitive lookup, normalization, and validation.
    
    Args:
        request: FastAPI Request object
        name: Header name (case-insensitive)
        default: Default value if header not present
        
    Returns:
        Normalized (lowercase) header value or default
        
    Raises:
        HTTPException: 400 if header value contains invalid characters
    """
    # Case-insensitive lookup
    value = None
    for header_name, header_value in request.headers.items():
        if header_name.lower() == name.lower():
            value = header_value
            break
    
    # Use default if not found
    if value is None:
        value = default
    
    # Normalize to lowercase
    normalized = value.lower()
    
    # Validate format
    if not PROJECT_USER_ID_PATTERN.match(normalized):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": f"Invalid {name}: must match [a-zA-Z0-9-]+",
                "received": value,
                "header": name
            }
        )
    
    return normalized


def validate_project_exists(project_id: str) -> None:
    """
    Validate that project exists, raise 412 if not.
    
    Args:
        project_id: Project identifier (already normalized)
        
    Raises:
        HTTPException: 412 if project doesn't exist
    """
    if not config.project_exists(project_id):
        raise HTTPException(
            status_code=412,
            detail={
                "error": "Precondition Failed",
                "message": f"Project '{project_id}' does not exist",
                "requested_project": project_id,
                "available_projects": config.list_available_projects()
            }
        )
```

**Tests**: Add to `tests/test_main.py`
```python
def test_extract_header_default()
def test_extract_header_case_insensitive()
def test_extract_header_normalization()
def test_extract_header_invalid_characters()
def test_validate_project_exists_success()
def test_validate_project_exists_failure()
```

**Validation**: Run `pytest tests/test_main.py::test_extract_header -v`

---

### Task 1.3: Add Workspace Setup Logic
**File**: `src/main.py` (add after header helpers)

**Estimated Time**: 1 hour

**Changes**:
```python
def setup_user_workspace(user_id: str, project_id: str) -> Path:
    """
    Setup user workspace directory with symlink to project's AGENTS.md if present.
    
    Creates directory structure:
    - /data/storage/{user_id}/
    - /data/storage/{user_id}/{project_id}/
    - Symlink to AGENTS.md if project has one
    
    Args:
        user_id: User identifier (already normalized)
        project_id: Project identifier (already normalized)
        
    Returns:
        Path to user's workspace directory
        
    Note: This function is idempotent and safe to call on every request.
    """
    # Get paths
    workspace_path = config.get_user_workspace_dir(user_id, project_id)
    project_agents_path = config.get_project_dir(project_id) / "AGENTS.md"
    workspace_agents_symlink = workspace_path / "AGENTS.md"
    
    # Create user directory if needed
    user_dir = config.get_storage_dir() / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured user directory exists: {user_dir}")
    
    # Create user+project workspace if needed
    workspace_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured workspace exists: {workspace_path}")
    
    # Handle AGENTS.md symlink
    if project_agents_path.exists():
        # Check if symlink already exists
        if workspace_agents_symlink.exists() or workspace_agents_symlink.is_symlink():
            # Symlink exists - verify it points to correct location
            if workspace_agents_symlink.is_symlink():
                current_target = workspace_agents_symlink.resolve()
                expected_target = project_agents_path.resolve()
                if current_target != expected_target:
                    logger.warning(
                        f"AGENTS.md symlink points to wrong location. "
                        f"Expected: {expected_target}, Got: {current_target}. "
                        f"Recreating symlink."
                    )
                    workspace_agents_symlink.unlink()
                    # Create relative symlink
                    relative_path = Path("../../../projects") / project_id / "AGENTS.md"
                    workspace_agents_symlink.symlink_to(relative_path)
                else:
                    logger.debug(f"AGENTS.md symlink already exists and is correct")
            else:
                logger.warning(
                    f"AGENTS.md exists as regular file, not symlink. "
                    f"Removing and creating symlink."
                )
                workspace_agents_symlink.unlink()
                relative_path = Path("../../../projects") / project_id / "AGENTS.md"
                workspace_agents_symlink.symlink_to(relative_path)
        else:
            # Create new symlink
            relative_path = Path("../../../projects") / project_id / "AGENTS.md"
            workspace_agents_symlink.symlink_to(relative_path)
            logger.info(f"Created AGENTS.md symlink: {workspace_agents_symlink} -> {relative_path}")
    else:
        logger.debug(f"Project {project_id} has no AGENTS.md, skipping symlink")
    
    return workspace_path
```

**Tests**: Add to `tests/test_main.py`
```python
def test_setup_user_workspace_creates_directories(tmp_path)
def test_setup_user_workspace_creates_symlink(tmp_path)
def test_setup_user_workspace_idempotent(tmp_path)
def test_setup_user_workspace_no_agents_md(tmp_path)
def test_setup_user_workspace_symlink_correction(tmp_path)
```

**Validation**: Run `pytest tests/test_main.py::test_setup_user_workspace -v`

---

## Phase 2: Update Main Request Handler

### Task 2.1: Modify Dynamic Route Handler
**File**: `src/main.py` - `dynamic_prompt_handler` function

**Estimated Time**: 1 hour

**Current Code** (line 111-126):
```python
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def dynamic_prompt_handler(request: Request, path: str):
    try:
        method = request.method
        full_path = f"/{path}" if path else "/"
        
        logger.info(f"Dynamic route request: {method} {full_path}")
        
        # Get prompts directory
        prompts_dir = config.get_prompts_dir()
        
        # Initialize router and load prompts
        router = DynamicRouter(prompts_dir)
        router.load_prompts()
```

**New Code**:
```python
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def dynamic_prompt_handler(request: Request, path: str):
    try:
        method = request.method
        full_path = f"/{path}" if path else "/"
        
        # Extract and validate headers
        project_id = extract_header(request, "x-project-id", "default")
        user_id = extract_header(request, "x-user-id", "anonymous")
        
        logger.info(f"Dynamic route request: {method} {full_path} (project={project_id}, user={user_id})")
        
        # Validate project exists
        validate_project_exists(project_id)
        
        # Get project's prompts directory
        prompts_dir = config.get_project_prompts_dir(project_id)
        
        # Initialize router and load prompts
        router = DynamicRouter(prompts_dir)
        router.load_prompts()
```

**Also Update** (line 225):
```python
        # Initialize executor
        executor = PromptExecutor(
            workspace_dir=config.get_workspace_dir(),  # OLD
            timeout=config.TIMEOUT_SECONDS
        )
```

**To**:
```python
        # Setup user workspace (creates dirs and symlinks as needed)
        workspace_dir = setup_user_workspace(user_id, project_id)
        
        # Initialize executor
        executor = PromptExecutor(
            workspace_dir=workspace_dir,
            timeout=config.TIMEOUT_SECONDS
        )
```

**Tests**: Update existing tests in `tests/test_main.py`
- Add `headers={"x-project-id": "test", "x-user-id": "test"}` to all `client.get()` calls
- Add new tests:
  ```python
  def test_dynamic_route_with_headers()
  def test_dynamic_route_default_project_user()
  def test_dynamic_route_case_insensitive_headers()
  def test_dynamic_route_invalid_project_412()
  def test_dynamic_route_invalid_project_id_format_400()
  ```

**Validation**: Run `pytest tests/test_main.py -v`

**Validation**: Run `pytest tests/test_main.py -v`

---

## Phase 3: Update OpenAPI Endpoints

### Task 3.1: Update OpenAPI JSON Endpoint
**File**: `src/main.py` - `openapi_document` function

**Estimated Time**: 45 minutes

**Current Code** (line 62-72):
```python
@app.get("/openapi.json")
async def openapi_document():
    """Dynamically generate OpenAPI 3.1 document from prompt files."""
    if not config.OPENAPI_ENABLED:
        raise HTTPException(status_code=404, detail={
            "error": "Not Found",
            "message": "OpenAPI endpoint is disabled",
        })

    prompts_dir = config.get_prompts_dir()
    result = generate_openapi(prompts_dir)
```

**New Code**:
```python
@app.get("/openapi.json")
async def openapi_document(request: Request, project: str = "default"):
    """
    Dynamically generate OpenAPI 3.1 document from project's prompt files.
    
    Query Parameters:
        project: Project ID (default: "default")
    """
    if not config.OPENAPI_ENABLED:
        raise HTTPException(status_code=404, detail={
            "error": "Not Found",
            "message": "OpenAPI endpoint is disabled",
        })
    
    # Normalize and validate project parameter
    project_id = project.lower()
    
    # Validate format
    if not PROJECT_USER_ID_PATTERN.match(project_id):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": f"Invalid project ID: must match [a-zA-Z0-9-]+",
                "received": project,
            }
        )
    
    # Check project exists
    if not config.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Not Found",
                "message": f"Project '{project_id}' does not exist",
                "requested_project": project_id,
                "available_projects": config.list_available_projects()
            }
        )
    
    # Get project's prompts directory
    prompts_dir = config.get_project_prompts_dir(project_id)
    result = generate_openapi(prompts_dir)
    
    if "errors" in result:
        return JSONResponse(status_code=500, content=result)
    return JSONResponse(content=result)
```

**Tests**: Add to `tests/test_openapi_endpoint.py`
```python
def test_openapi_default_project()
def test_openapi_explicit_project()
def test_openapi_case_insensitive_project()
def test_openapi_nonexistent_project_404()
def test_openapi_invalid_project_format_400()
```

**Validation**: Run `pytest tests/test_openapi_endpoint.py -v`

---

### Task 3.2: Update OpenAPI Swagger UI Endpoint
**File**: `src/main.py` - `openapi_swagger_ui` function

**Estimated Time**: 30 minutes

**Current Code** (line 75-107):
```python
@app.get("/openapi")
async def openapi_swagger_ui():
    """Serve Swagger UI that consumes the dynamic /openapi.json."""
    if not config.OPENAPI_ENABLED:
        raise HTTPException(...)
    html = """
    ...
    window.onload = () => {
        const ui = SwaggerUIBundle({
            url: '/openapi.json',
    ...
```

**New Code**:
```python
@app.get("/openapi")
async def openapi_swagger_ui(request: Request, project: str = "default"):
    """
    Serve Swagger UI that consumes the dynamic /openapi.json.
    
    Query Parameters:
        project: Project ID (default: "default")
    """
    if not config.OPENAPI_ENABLED:
        raise HTTPException(status_code=404, detail={
            "error": "Not Found",
            "message": "OpenAPI endpoint is disabled",
        })
    
    # Normalize and validate project parameter
    project_id = project.lower()
    
    # Validate format
    if not PROJECT_USER_ID_PATTERN.match(project_id):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": f"Invalid project ID: must match [a-zA-Z0-9-]+",
                "received": project,
            }
        )
    
    # Check project exists
    if not config.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Not Found",
                "message": f"Project '{project_id}' does not exist",
                "requested_project": project_id,
                "available_projects": config.list_available_projects()
            }
        )
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Codex API – Swagger UI (Project: {project_id})</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.onload = () => {{
                const ui = SwaggerUIBundle({{
                    url: '/openapi.json?project={project_id}',
                    dom_id: '#swagger-ui',
                    presets: [SwaggerUIBundle.presets.apis],
                    layout: 'BaseLayout'
                }});
                window.ui = ui;
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
```

**Tests**: Add to `tests/test_openapi_swagger_ui.py`
```python
def test_swagger_ui_default_project()
def test_swagger_ui_explicit_project()
def test_swagger_ui_contains_project_in_url()
def test_swagger_ui_nonexistent_project_404()
```

**Validation**: Run `pytest tests/test_openapi_swagger_ui.py -v`

---

### Task 3.3: Verify OpenAPI Generator (No Changes Needed)
**File**: `src/openapi/generator.py`

**Estimated Time**: 15 minutes

**Analysis**: 
- `generate_openapi(prompts_dir: Path)` already takes directory as parameter ✅
- No hardcoded paths ✅
- Works with any prompts directory ✅

**Action**: Verify tests still pass with project-specific directories

**Tests**: Run existing tests
```bash
pytest tests/test_openapi_generator.py -v
```

**Expected**: All tests should pass (they use tmp_path or fixtures)

---

## Phase 4: Update All Tests

### Task 4.1: Update E2E Tests
**File**: `tests/test_e2e.py`

**Estimated Time**: 1 hour

**Current Code**:
```python
def test_e2e_root_endpoint():
    with running_server(port=8002) as server:
        response = httpx.get(f"{server.base_url}/")
```

**Changes**:
Add headers to all HTTP requests:
```python
HEADERS = {"x-project-id": "test", "x-user-id": "test"}

def test_e2e_root_endpoint():
    with running_server(port=8002) as server:
        response = httpx.get(f"{server.base_url}/")  # No headers needed for root
        ...

def test_e2e_dynamic_route():
    with running_server(port=8003) as server:
        response = httpx.get(f"{server.base_url}/some-route", headers=HEADERS)
        ...
```

**Add New Tests**:
```python
def test_e2e_default_project_user():
    """Test that requests work without headers (default project/user)"""
    with running_server(port=8010) as server:
        # Should work with default project
        response = httpx.get(f"{server.base_url}/hi")
        # Check it uses default project

def test_e2e_case_insensitive_headers():
    """Test case-insensitive header names"""
    with running_server(port=8011) as server:
        headers = {"X-PROJECT-ID": "TEST", "X-USER-ID": "TEST"}
        response = httpx.get(f"{server.base_url}/hi", headers=headers)
        assert response.status_code == 200

def test_e2e_invalid_project_412():
    """Test non-existent project returns 412"""
    with running_server(port=8012) as server:
        headers = {"x-project-id": "nonexistent", "x-user-id": "test"}
        response = httpx.get(f"{server.base_url}/hi", headers=headers)
        assert response.status_code == 412
        data = response.json()
        assert "available_projects" in data["detail"]

def test_e2e_workspace_isolation():
    """Verify workspace is created in correct location"""
    with running_server(port=8013) as server:
        headers = {"x-project-id": "test", "x-user-id": "testuser"}
        response = httpx.get(f"{server.base_url}/hi", headers=headers)
        # Check that workspace was created at data/storage/testuser/test/
        workspace = Path("data/storage/testuser/test")
        assert workspace.exists()
```

**Validation**: Run `pytest tests/test_e2e.py -v`

---

### Task 4.2: Update Integration Tests
**File**: `tests/test_main.py`

**Estimated Time**: 1.5 hours

**Changes**:
1. Add headers to ALL `client.get()`, `client.post()`, etc. calls
2. Update mocks to account for new helper functions
3. Add comprehensive tests for new functionality

**Example Updates**:
```python
def test_root_endpoint():
    """Test the root endpoint returns API information"""
    response = client.get("/")  # Root doesn't need headers
    assert response.status_code == 200
    ...

def test_dynamic_route_success():
    """Test dynamic route with successful execution"""
    # Add headers
    headers = {"x-project-id": "test", "x-user-id": "test"}
    
    # Mock config methods
    with patch("src.config.config.project_exists", return_value=True):
        with patch("src.config.config.get_project_prompts_dir", return_value=Path("/tmp/test/prompts")):
            with patch("src.main.setup_user_workspace", return_value=Path("/tmp/workspace")):
                with patch("src.prompts.router.DynamicRouter.load_prompts"):
                    with patch("src.prompts.router.DynamicRouter.match_route", return_value=mock_match):
                        with patch("src.prompts.executor.PromptExecutor.execute", return_value=mock_result):
                            response = client.get("/test", headers=headers)
                            assert response.status_code == 200
```

**Add New Tests**:
```python
def test_extract_header_default():
    """Test header extraction with default value"""
    ...

def test_extract_header_case_insensitive():
    """Test case-insensitive header lookup"""
    ...

def test_validate_project_exists_success():
    """Test project validation passes for existing project"""
    ...

def test_validate_project_exists_failure():
    """Test project validation raises 412 for non-existent project"""
    ...

def test_setup_user_workspace():
    """Test workspace setup creates directories and symlinks"""
    ...

def test_dynamic_route_invalid_project():
    """Test 412 error for non-existent project"""
    headers = {"x-project-id": "nonexistent", "x-user-id": "test"}
    with patch("src.config.config.project_exists", return_value=False):
        with patch("src.config.config.list_available_projects", return_value=["test", "default"]):
            response = client.get("/test", headers=headers)
            assert response.status_code == 412

def test_dynamic_route_invalid_project_format():
    """Test 400 error for invalid project ID format"""
    headers = {"x-project-id": "invalid@project", "x-user-id": "test"}
    response = client.get("/test", headers=headers)
    assert response.status_code == 400
```

**Validation**: Run `pytest tests/test_main.py -v`

---

### Task 4.3: Update Unit Tests (Prompt Loader, Router, etc.)
**Files**: `tests/test_prompt_loader.py`, `tests/test_router.py`, `tests/test_openapi_generator.py`, etc.

**Estimated Time**: 30 minutes

**Analysis**:
- `test_prompt_loader.py` - Uses `FIXTURES_DIR`, no changes needed ✅
- `test_router.py` - Uses `FIXTURES_DIR`, no changes needed ✅
- `test_openapi_generator.py` - Line 9 uses `config.get_prompts_dir()` ⚠️
- `test_executor.py` - May use workspace_dir ⚠️
- Other test files - Review for config usage

**Changes for `test_openapi_generator.py`**:
```python
# OLD (line 9)
prompts_dir = Path(config.get_prompts_dir())

# NEW - Use test project
prompts_dir = config.get_project_prompts_dir("test")
# OR use fixtures
prompts_dir = Path(__file__).parent / "fixtures" / "prompts"
```

**Action Items**:
1. Search all test files for `config.get_prompts_dir()`
2. Search all test files for `config.get_workspace_dir()`
3. Replace with project-specific calls or fixtures
4. Ensure tests don't depend on default project structure

**Validation**: Run `pytest tests/ -v` (full suite)

---

### Task 4.4: Create Config Tests
**File**: `tests/test_config.py` (NEW FILE)

**Estimated Time**: 45 minutes

**Create New Test File**:
```python
"""
Tests for configuration module
"""
import pytest
from pathlib import Path
from src.config import config


def test_get_projects_dir():
    """Test get_projects_dir returns correct path"""
    projects_dir = config.get_projects_dir()
    assert projects_dir.name == "projects"
    assert "data" in str(projects_dir)


def test_get_storage_dir():
    """Test get_storage_dir returns correct path"""
    storage_dir = config.get_storage_dir()
    assert storage_dir.name == "storage"


def test_get_project_dir():
    """Test get_project_dir builds correct path"""
    project_dir = config.get_project_dir("test")
    assert project_dir.name == "test"
    assert project_dir.parent.name == "projects"


def test_get_project_dir_case_insensitive():
    """Test project dir is case-insensitive"""
    assert config.get_project_dir("TEST") == config.get_project_dir("test")
    assert config.get_project_dir("TeSt") == config.get_project_dir("test")


def test_get_project_prompts_dir():
    """Test get_project_prompts_dir builds correct path"""
    prompts_dir = config.get_project_prompts_dir("test")
    assert prompts_dir.name == "prompts"
    assert prompts_dir.parent.name == "test"


def test_get_user_workspace_dir():
    """Test get_user_workspace_dir builds correct path"""
    workspace = config.get_user_workspace_dir("user1", "test")
    assert workspace.name == "test"
    assert workspace.parent.name == "user1"
    assert workspace.parent.parent.name == "storage"


def test_get_user_workspace_dir_case_insensitive():
    """Test user workspace is case-insensitive"""
    w1 = config.get_user_workspace_dir("USER", "PROJECT")
    w2 = config.get_user_workspace_dir("user", "project")
    assert w1 == w2


def test_list_available_projects(tmp_path):
    """Test list_available_projects returns project directories"""
    # This test should use actual data/projects/ directory
    projects = config.list_available_projects()
    assert isinstance(projects, list)
    assert "test" in projects or "default" in projects


def test_project_exists():
    """Test project_exists checks directory existence"""
    # Should exist (created during data migration)
    assert config.project_exists("test") == True
    assert config.project_exists("default") == True
    
    # Should not exist
    assert config.project_exists("nonexistent") == False


def test_project_exists_case_insensitive():
    """Test project_exists is case-insensitive"""
    assert config.project_exists("TEST") == config.project_exists("test")
```

**Validation**: Run `pytest tests/test_config.py -v`

---

## Phase 5: Cleanup & Documentation

### Task 5.1: Deprecate Old Configuration
**File**: `src/config.py`

**Estimated Time**: 15 minutes

**Changes**:
```python
# Add deprecation warning to old method
import warnings

@classmethod
def get_prompts_dir(cls) -> Path:
    """
    DEPRECATED: Use get_project_prompts_dir() instead.
    
    Get prompts directory, creating it if it doesn't exist.
    This method is deprecated and will be removed in future versions.
    """
    warnings.warn(
        "get_prompts_dir() is deprecated, use get_project_prompts_dir(project_id) instead",
        DeprecationWarning,
        stacklevel=2
    )
    prompts_dir = cls.WORKSPACE_DIR / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    return prompts_dir
```

**Note**: Keep `PROMPTS_DIR` class variable for now (some tests may reference it)

**Validation**: Run full test suite, check for deprecation warnings

---

### Task 5.2: Update Root Endpoint Documentation
**File**: `src/main.py` - `root()` function

**Estimated Time**: 10 minutes

**Current Code**:
```python
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Codex API",
        "version": "0.3.0",
        ...
        "prompts_dir": str(config.get_prompts_dir())
    }
```

**New Code**:
```python
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Codex API",
        "version": "0.3.0",
        "phase": "3 - Dynamic Prompt-Based Routing with Multi-Tenancy",
        "description": "REST API wrapper for AI CLI tools with multi-project and multi-user support",
        "endpoints": {
            "/": "API information",
            "/<dynamic>": "Dynamic routes based on project prompts"
        },
        "headers": {
            "x-project-id": "Project identifier (default: 'default')",
            "x-user-id": "User identifier (default: 'anonymous')"
        },
        "provider": config.AI_PROVIDER,
        "available_providers": ProviderFactory.list_providers(),
        "available_projects": config.list_available_projects(),
        "projects_dir": str(config.get_projects_dir()),
        "storage_dir": str(config.get_storage_dir())
    }
```

**Validation**: `curl http://localhost:8000/` and verify JSON structure

---

### Task 5.3: Update README.md
**File**: `README.md`

**Estimated Time**: 30 minutes

**Add Section**: "Multi-Project and Multi-User Support"

```markdown
## Multi-Project and Multi-User Support

### Headers

#### `x-project-id` (optional)
- **Format**: `[a-zA-Z0-9-]+` (case-insensitive)
- **Default**: `default`
- **Description**: Specifies which project's prompts to use

#### `x-user-id` (optional)
- **Format**: `[a-zA-Z0-9-]+` (case-insensitive)
- **Default**: `anonymous`
- **Description**: Identifies the user for workspace isolation

### Folder Structure

\```
data/
├── projects/
│   ├── default/
│   │   ├── prompts/           # Prompt files for default project
│   │   └── AGENTS.md          # Optional agent configuration
│   └── test/
│       └── prompts/           # Prompt files for test project
└── storage/
    ├── anonymous/
    │   └── default/           # Workspace for anonymous user
    └── {user-id}/
        └── {project-id}/      # Isolated workspace per user+project
\```

### Examples

\```bash
# Use default project and anonymous user
curl http://localhost:8000/hi

# Specify project
curl -H "x-project-id: test" http://localhost:8000/hi

# Specify project and user
curl -H "x-project-id: myproject" \\
     -H "x-user-id: alice" \\
     http://localhost:8000/greet/Alice

# OpenAPI for specific project
curl http://localhost:8000/openapi.json?project=test

# View Swagger UI for project
open http://localhost:8000/openapi?project=test
\```

### Creating a New Project

1. Create project directory: `mkdir -p data/projects/myproject/prompts`
2. Add prompt files: `data/projects/myproject/prompts/*.md`
3. (Optional) Add agent config: `data/projects/myproject/AGENTS.md`
4. Access via header: `-H "x-project-id: myproject"`
```

**Validation**: Review README in GitHub-flavored markdown viewer

---

### Task 5.4: Verify Data Migration
**Checklist**:

**Estimated Time**: 15 minutes

**Verify**:
- [ ] `/data/projects/test/prompts/` exists
- [ ] Test prompts migrated: `test-body-*.md`, `user-profile.md`
- [ ] `/data/projects/default/prompts/` exists  
- [ ] Default prompts exist: `hi.md`, `calc.md`, `greet.md`, `analyze.md`, `any.md`
- [ ] `/data/projects/default/AGENTS.md` exists
- [ ] `/data/storage/anonymous/default/` can be created
- [ ] `/data/storage/anonymous/test/` can be created

**Action**: Run migration verification script or manual checks

```bash
# Verify test project
ls -la data/projects/test/prompts/
ls -la data/projects/test/AGENTS.md

# Verify default project  
ls -la data/projects/default/prompts/
ls -la data/projects/default/AGENTS.md

# Verify storage directory exists
ls -la data/storage/
```

---

## Phase 6: Final Integration Testing

### Task 6.1: Run Full Test Suite
**Estimated Time**: 30 minutes

**Command**:
```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test categories
pytest tests/test_config.py -v
pytest tests/test_main.py -v
pytest tests/test_e2e.py -v
pytest tests/test_openapi_*.py -v
```

**Expected**: All tests pass ✅

**If failures**: Debug and fix before proceeding

---

### Task 6.2: Manual Integration Testing
**Estimated Time**: 45 minutes

**Test Scenarios**:

1. **Default Project/User**:
   ```bash
   curl http://localhost:8000/hi
   # Should use default project and anonymous user
   # Check workspace: data/storage/anonymous/default/
   ```

2. **Explicit Project/User**:
   ```bash
   curl -H "x-project-id: test" -H "x-user-id: alice" http://localhost:8000/hi
   # Check workspace: data/storage/alice/test/
   ```

3. **Case-Insensitive Headers**:
   ```bash
   curl -H "X-PROJECT-ID: TEST" -H "X-USER-ID: BOB" http://localhost:8000/hi
   # Should normalize to test/bob
   ```

4. **Invalid Project (412)**:
   ```bash
   curl -H "x-project-id: nonexistent" http://localhost:8000/hi
   # Should return 412 with available_projects list
   ```

5. **Invalid Format (400)**:
   ```bash
   curl -H "x-project-id: invalid@project" http://localhost:8000/hi
   # Should return 400
   ```

6. **AGENTS.md Symlink**:
   ```bash
   curl -H "x-project-id: default" -H "x-user-id: test" http://localhost:8000/hi
   ls -la data/storage/test/default/AGENTS.md
   # Should be a symlink to ../../../projects/default/AGENTS.md
   ```

7. **OpenAPI with Project**:
   ```bash
   curl "http://localhost:8000/openapi.json?project=test"
   # Should return OpenAPI doc for test project
   
   open "http://localhost:8000/openapi?project=test"
   # Should show Swagger UI for test project
   ```

---

### Task 6.3: Performance & Stress Testing (Optional)
**Estimated Time**: 30 minutes

**Test**: Concurrent requests with different users/projects
```bash
# Use Apache Bench or similar
ab -n 100 -c 10 -H "x-project-id: test" -H "x-user-id: user1" http://localhost:8000/hi

# Check workspace creation is thread-safe
for i in {1..50}; do
    curl -H "x-project-id: test" -H "x-user-id: user$i" http://localhost:8000/hi &
done
wait

# Verify all workspaces created
ls data/storage/ | wc -l
```

---

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Task 1.1: Add config methods (30 min)
- [ ] Task 1.2: Add header helpers (45 min)
- [ ] Task 1.3: Add workspace setup (1 hour)
- [ ] **Validation**: Run tests, verify config methods work

### Phase 2: Main Handler
- [ ] Task 2.1: Update dynamic route handler (1 hour)
- [ ] **Validation**: Run tests with headers, verify 412 errors

### Phase 3: OpenAPI
- [ ] Task 3.1: Update /openapi.json (45 min)
- [ ] Task 3.2: Update /openapi UI (30 min)
- [ ] Task 3.3: Verify generator (15 min)
- [ ] **Validation**: Test OpenAPI with ?project= parameter

### Phase 4: Tests
- [ ] Task 4.1: Update E2E tests (1 hour)
- [ ] Task 4.2: Update integration tests (1.5 hours)
- [ ] Task 4.3: Update unit tests (30 min)
- [ ] Task 4.4: Create config tests (45 min)
- [ ] **Validation**: Full test suite passes

### Phase 5: Cleanup
- [ ] Task 5.1: Deprecate old config (15 min)
- [ ] Task 5.2: Update root endpoint (10 min)
- [ ] Task 5.3: Update README (30 min)
- [ ] Task 5.4: Verify data migration (15 min)
- [ ] **Validation**: Documentation is complete

### Phase 6: Final Testing
- [ ] Task 6.1: Run full test suite (30 min)
- [ ] Task 6.2: Manual integration testing (45 min)
- [ ] Task 6.3: Performance testing (30 min - optional)
- [ ] **Validation**: All scenarios work end-to-end

---

## Total Estimated Time

- **Phase 1**: 2.25 hours
- **Phase 2**: 1 hour
- **Phase 3**: 1.5 hours
- **Phase 4**: 4 hours
- **Phase 5**: 1.25 hours
- **Phase 6**: 1.75 hours

**Total**: ~12 hours (1.5 days)

---

## Success Criteria

1. ✅ All requests accept `x-project-id` header (case-insensitive)
2. ✅ All requests accept `x-user-id` header (case-insensitive)
3. ✅ Prompts loaded from `/data/projects/{project_id}/prompts/`
4. ✅ Workspaces created at `/data/storage/{user_id}/{project_id}/`
5. ✅ AGENTS.md symlinked when present
6. ✅ HTTP 412 for non-existent project (routes)
7. ✅ HTTP 404 for non-existent project (OpenAPI)
8. ✅ HTTP 400 for invalid ID format
9. ✅ OpenAPI supports `?project=` parameter
10. ✅ All existing tests pass with headers
11. ✅ Default project/user behavior works (no headers)
12. ✅ Complete workspace isolation per user+project
13. ✅ Full test coverage (unit + integration + E2E)
14. ✅ Documentation updated (README + code comments)

---

## Risk Mitigation

### Risk: Breaking existing tests
**Mitigation**: Update tests incrementally, run after each change

### Risk: Symlink issues on different OS
**Mitigation**: Test on macOS (current), add TODO for Windows testing

### Risk: Race conditions in workspace creation
**Mitigation**: Use `mkdir(exist_ok=True)` - filesystem handles atomicity

### Risk: Case sensitivity on different filesystems
**Mitigation**: Normalize all IDs to lowercase immediately

### Risk: Old code still uses `get_prompts_dir()`
**Mitigation**: Add deprecation warning, search codebase for usage

---

## Notes

- No changes needed to `loader.py`, `router.py`, `executor.py` (they already accept paths as parameters)
- Config changes are backward compatible (old methods still work)
- Test project already migrated to `/data/projects/test/`
- Default project exists at `/data/projects/default/`
- All tests should target `test` project with headers
