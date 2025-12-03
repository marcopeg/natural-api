# Task 004 Execution Plan: Dynamic Prompt-Based Routing

## Overview
Implement a dynamic routing system that maps HTTP requests to AI prompts stored as Markdown files with YAML frontmatter. The system will support variable substitution, multiple HTTP verbs, and fallback routing based on filenames.

---

## Phase 1: Core Infrastructure (Foundation)

### 1.1 Create Prompt Loader Module
**File:** `src/prompts/loader.py`

**Components:**
- `PromptMetadata` dataclass:
  - `filename: str` (without .md extension)
  - `filepath: Path` (full path to file)
  - `verb: str` (HTTP method, default "GET")
  - `route: str | None` (explicit route or None for fallback)
  - `model: str | None` (model override)
  - `agent: str | None` (provider override)
  - `raw_content: str` (full file content after frontmatter)

- `load_prompts(prompts_dir: Path) -> list[PromptMetadata]`:
  - Scan `*.md` files in directory
  - Parse YAML frontmatter using `python-frontmatter` library
  - Extract filename (without extension)
  - Extract config fields with defaults
  - Log loaded prompts at DEBUG level
  - Handle malformed files gracefully (skip or use defaults)
  - Return list of PromptMetadata objects

**Dependencies:**
```python
pip install python-frontmatter
```

**Error Handling:**
- Skip files that can't be read (log warning)
- Skip files with invalid YAML (log warning, use empty frontmatter)
- Always return a list (even if empty)

**Testing:**
- Create `tests/fixtures/prompts/` with test files
- Test valid frontmatter parsing
- Test missing frontmatter fields (use defaults)
- Test malformed YAML (graceful degradation)
- Test empty directory

---

### 1.2 Create Variable Substitution Module
**File:** `src/prompts/variables.py`

**Components:**
- `substitute_variables(template: str, variables: dict[str, str]) -> str`:
  - Use regex to find `${var}` and `${var:default}` patterns
  - Replace with values from variables dict
  - If variable not found and no default: use empty string
  - If variable not found but has default: use default value
  - Return processed string

**Regex Pattern:**
```python
\$\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]*))?\}
```
- Group 1: variable name
- Group 2: default value (optional)

**Examples:**
```python
substitute_variables("Hello ${name}!", {"name": "Alice"})
# → "Hello Alice!"

substitute_variables("Role: ${role:guest}", {})
# → "Role: guest"

substitute_variables("${greeting:Hi} ${name}", {"name": "Bob"})
# → "Hi Bob"
```

**Testing:**
- Test simple variable substitution
- Test variables with defaults
- Test missing variables without defaults (empty string)
- Test multiple variables in same string
- Test edge cases (nested braces, special chars in defaults)

---

### 1.3 Update Config Module
**File:** `src/config.py`

**Changes:**
- Add `PROMPTS_DIR: Path = WORKSPACE_DIR / "prompts"`
- Add method `get_prompts_dir() -> Path` (create if not exists)
- Add `LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")`

**Testing:**
- Verify prompts directory creation
- Verify default path is `./data/prompts`
- Test environment variable override

---

## Phase 2: Routing System (Core Feature)

### 2.1 Create Route Matcher Module
**File:** `src/prompts/router.py`

**Components:**
- `RouteMatch` dataclass:
  - `prompt: PromptMetadata`
  - `match_type: str` ("explicit" or "fallback")
  - `path_params: dict[str, str]` (extracted from path)

- `DynamicRouter` class:
  - `__init__(self, prompts_dir: Path)`
  - `load_prompts(self) -> None`: Load prompts from directory
  - `match_route(self, method: str, path: str) -> RouteMatch | None`:
    - Try explicit route matching first
    - Try fallback filename matching second
    - Return None if no match
  - `_match_explicit(method, path) -> RouteMatch | None`
  - `_match_fallback(method, path) -> RouteMatch | None`
  - `_extract_path_params(pattern, path) -> dict[str, str]`

**Route Matching Logic:**

1. **Explicit matching:**
   - Iterate through prompts with `route` defined
   - Check if `verb` matches request method (case-insensitive)
   - Use path pattern matching (see below)
   - Return first match

2. **Fallback matching:**
   - Iterate through all prompts
   - Generate route: `/{filename}`
   - Only match GET requests
   - Return first match

3. **Path pattern matching:**
   - Use regex to convert FastAPI-style patterns to regex
   - `{name}` → `(?P<name>[^/]+)` (match until next slash)
   - `{path:path}` → `(?P<path>.+)` (match everything)
   - Extract named groups as path parameters

**Logging:**
- Log all loaded prompts (count, list) at INFO level
- Log match result (prompt filename, match type) at INFO level
- Log no match at DEBUG level

**Testing:**
- Test explicit route matching
- Test fallback filename matching
- Test path parameter extraction
- Test verb matching (case-insensitive)
- Test first-match priority
- Test no match returns None
- Test multiple path parameters

---

### 2.2 Create Prompt Execution Module
**File:** `src/prompts/executor.py`

**Components:**
- `PromptExecutor` class:
  - `__init__(self, workspace_dir: Path, timeout: int)`
  - `execute(self, prompt: PromptMetadata, path_params: dict[str, str]) -> AIProviderResult`:
    - Substitute variables in prompt body
    - Create AI provider (use prompt.agent or default)
    - Check provider availability
    - Execute prompt with provider
    - Return AIProviderResult

**Steps:**
1. Get prompt content (`prompt.raw_content`)
2. Substitute variables: `substitute_variables(content, path_params)`
3. Create provider: `ProviderFactory.create(agent or default)`
4. Check: `provider.is_available()`
5. Execute: `provider.execute(processed_prompt)`
6. Return result

**Provider Selection:**
- If `prompt.agent` is set: use that provider
- Else: use `config.AI_PROVIDER`

**Model Override:**
- If `prompt.model` is set: pass to provider somehow
- **Challenge:** Current provider interface doesn't support model parameter
- **Solution:** Add model support in Phase 3

**Testing:**
- Test variable substitution integration
- Test provider selection (default vs override)
- Test provider availability check
- Mock provider execution
- Test timeout handling

---

## Phase 3: API Integration (FastAPI Endpoint)

### 3.1 Create Dynamic Endpoint Handler
**File:** `src/main.py`

**New endpoint:**
```python
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def dynamic_prompt_handler(request: Request, path: str):
    """Handle all dynamic prompt-based routes"""
```

**Implementation:**
1. Get request method and path
2. Initialize DynamicRouter with prompts directory
3. Load prompts (every request - no caching)
4. Match route: `router.match_route(method, f"/{path}")`
5. If no match: raise HTTPException 404
6. Execute prompt with PromptExecutor
7. Handle errors (timeout, failure, unavailable)
8. Return plain text response

**Response:**
```python
from fastapi.responses import PlainTextResponse
return PlainTextResponse(result.stdout)
```

**Error Handling:**
```python
# No route match
if not match:
    raise HTTPException(404, detail="No prompt found for this route")

# Provider unavailable
if not provider.is_available():
    raise HTTPException(503, detail={...})

# Timeout
if result.returncode == 124:
    raise HTTPException(408, detail={...})

# Execution failure
if not result.success:
    raise HTTPException(500, detail={...})
```

**Logging:**
```python
logger.info(f"Matched prompt: {match.prompt.filename} ({match.match_type})")
logger.debug(f"Path params: {match.path_params}")
logger.debug(f"AI stdout: {result.stdout}")
```

**Route Priority:**
- FastAPI evaluates routes in order of registration
- Existing static routes (`/hello`, `/test-write`) registered first
- Dynamic catch-all route registered last
- This ensures backward compatibility

**Testing:**
- Mock DynamicRouter and PromptExecutor
- Test successful request flow
- Test 404 when no match
- Test 500 on AI failure
- Test 503 when provider unavailable
- Test 408 on timeout

---

### 3.2 Setup Logging Configuration
**File:** `src/main.py` or new `src/logging_config.py`

**Configuration:**
```python
import logging

logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

**Loggers:**
- `src.main` - API endpoint logs
- `src.prompts.loader` - Prompt loading logs
- `src.prompts.router` - Route matching logs
- `src.prompts.executor` - Prompt execution logs

---

## Phase 4: Provider Enhancement (Model Support)

### 4.1 Add Model Parameter to Provider Interface
**File:** `src/providers/base.py`

**Changes:**
- Update `execute()` signature: `execute(prompt: str, model: str | None = None)`
- Update `AIProvider` abstract class
- Document model parameter usage

**File:** `src/providers/codex.py`

**Changes:**
- Update `execute()` implementation
- If model parameter provided: add `-m {model}` to codex command
- Example: `codex exec -m gpt-5.1-codex-mini "{prompt}"`

**Testing:**
- Test execute with model override
- Test execute without model (use default)
- Verify correct CLI flags in subprocess call

---

### 4.2 Update PromptExecutor to Pass Model
**File:** `src/prompts/executor.py`

**Changes:**
```python
result = provider.execute(processed_prompt, model=prompt.model)
```

**Testing:**
- Test model override from prompt frontmatter
- Test execution without model override

---

## Phase 5: Testing (Comprehensive Test Suite)

### 5.1 Unit Tests for Prompt Loader
**File:** `tests/test_prompt_loader.py`

**Fixtures:**
Create in `tests/fixtures/prompts/`:
- `valid.md` - Full frontmatter with all fields
- `minimal.md` - No frontmatter
- `partial.md` - Some frontmatter fields
- `invalid.md` - Malformed YAML
- `empty.md` - Empty file

**Tests:**
- `test_load_valid_prompts()`
- `test_load_minimal_prompts()` - defaults applied
- `test_load_partial_prompts()` - mixed fields
- `test_load_invalid_yaml()` - graceful handling
- `test_load_empty_directory()`
- `test_filename_extraction()`

---

### 5.2 Unit Tests for Variable Substitution
**File:** `tests/test_variables.py`

**Tests:**
- `test_simple_substitution()`
- `test_substitution_with_default()`
- `test_missing_variable_no_default()`
- `test_missing_variable_with_default()`
- `test_multiple_variables()`
- `test_no_variables()`
- `test_edge_cases()` - special chars, empty defaults

---

### 5.3 Unit Tests for Route Matching
**File:** `tests/test_router.py`

**Tests:**
- `test_explicit_route_match()`
- `test_fallback_route_match()`
- `test_path_parameter_extraction()`
- `test_multiple_path_parameters()`
- `test_verb_matching_case_insensitive()`
- `test_first_match_priority()`
- `test_no_match_returns_none()`
- `test_path_converter_matching()` - `{path:path}`

---

### 5.4 Unit Tests for Prompt Executor
**File:** `tests/test_executor.py`

**Tests:**
- `test_execute_with_path_params()`
- `test_execute_with_agent_override()`
- `test_execute_with_model_override()`
- `test_provider_unavailable()`
- Mock provider for all tests

---

### 5.5 Integration Tests for API Endpoint
**File:** `tests/test_main.py` (update existing)

**Tests:**
- `test_dynamic_route_explicit()`
- `test_dynamic_route_fallback()`
- `test_dynamic_route_with_params()`
- `test_dynamic_route_404()`
- `test_dynamic_route_different_verbs()`
- `test_backward_compatibility()` - existing routes still work
- Mock DynamicRouter and PromptExecutor

---

### 5.6 E2E Tests with Real Prompts
**File:** `tests/test_e2e_prompts.py`

**Setup:**
- Start real uvicorn server
- Create test prompts in temporary directory
- Configure server to use test prompts directory

**Tests:**
- `test_e2e_simple_prompt()`
- `test_e2e_prompt_with_variables()`
- `test_e2e_fallback_route()`
- `test_e2e_model_override()`
- `test_e2e_404_no_match()`

**Cleanup:**
- Remove test prompts directory
- Stop server

---

## Phase 6: Documentation & Final Testing

### 6.1 Update README
**File:** `README.md`

**Additions:**
- Document prompt file format
- Document frontmatter fields
- Document variable substitution syntax
- Provide examples
- Document environment variables

---

### 6.2 Create Example Prompts
**Files in:** `data/prompts/`

**Examples:**
1. `hello.md` - Simple greeting (fallback route)
2. `greet.md` - Greeting with name parameter
3. `calculate.md` - Calculator with explicit route
4. `user-profile.md` - User profile with multiple params

---

### 6.3 Run Full Test Suite
```bash
# Activate venv
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src --cov-report=term-missing
```

**Success Criteria:**
- All tests pass
- Coverage > 80%
- No linting errors
- Example prompts work in manual testing

---

### 6.4 Manual Testing Checklist
```bash
# Start server
uvicorn src.main:app --reload

# Test fallback route
curl http://localhost:8000/hi

# Test explicit route
curl http://localhost:8000/calculator

# Test with path parameters
curl http://localhost:8000/greet/Alice

# Test different HTTP verb
curl -X POST http://localhost:8000/process

# Test 404
curl http://localhost:8000/nonexistent

# Test existing endpoints still work
curl http://localhost:8000/hello
curl http://localhost:8000/test-write
```

---

## Implementation Order Summary

```
1. Install dependencies (python-frontmatter)
2. Create src/prompts/ directory structure
3. Implement loader.py (PromptMetadata, load_prompts)
4. Implement variables.py (substitute_variables)
5. Update config.py (PROMPTS_DIR, LOG_LEVEL)
6. Implement router.py (DynamicRouter, RouteMatch)
7. Implement executor.py (PromptExecutor)
8. Update base.py (add model parameter)
9. Update codex.py (support model parameter)
10. Update main.py (add dynamic endpoint)
11. Setup logging configuration
12. Create test fixtures
13. Write unit tests (loader, variables, router, executor)
14. Write integration tests (API endpoint)
15. Write E2E tests (full flow)
16. Update documentation
17. Create example prompts
18. Run full test suite
19. Manual testing
20. Final validation
```

---

## Dependencies to Install

```bash
pip install python-frontmatter
```

Update `requirements.txt`:
```
fastapi
uvicorn[standard]
python-frontmatter
pytest
pytest-asyncio
httpx
```

---

## Estimated Effort

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | Core Infrastructure | 2-3 hours |
| Phase 2 | Routing System | 2-3 hours |
| Phase 3 | API Integration | 1-2 hours |
| Phase 4 | Provider Enhancement | 1 hour |
| Phase 5 | Testing | 3-4 hours |
| Phase 6 | Documentation | 1 hour |
| **Total** | | **10-13 hours** |

---

## Risk Mitigation

### Risk: Path pattern matching complexity
**Mitigation:** Start with simple `{name}` patterns, add `{path:path}` later if time permits

### Risk: Provider model parameter not working
**Mitigation:** Test with codex CLI first, verify flag syntax works

### Risk: Variable substitution edge cases
**Mitigation:** Comprehensive unit tests, document limitations

### Risk: Route conflicts with existing endpoints
**Mitigation:** Register dynamic route last, test backward compatibility

### Risk: Malformed prompt files breaking server
**Mitigation:** Graceful error handling, skip invalid files with logging

---

## Success Criteria

- ✅ All tests pass (`pytest tests/ -v`)
- ✅ Example prompts work correctly
- ✅ Existing endpoints still functional
- ✅ Variable substitution works with defaults
- ✅ Route matching handles explicit and fallback
- ✅ Error handling returns proper HTTP status codes
- ✅ Logging provides useful debugging information
- ✅ Documentation is complete and accurate
- ✅ Code follows project conventions
- ✅ No security warnings (even though security not implemented)

---

## Next Steps After Task 004

Based on the documented "Future" items:

1. **Request body integration** - POST/PUT data → prompt variables
2. **Query parameter support** - `?role=admin` → `${role}`
3. **Prompt caching** - File watcher, hot reload
4. **Frontmatter validation** - JSON schema, startup validation
5. **Debug endpoint** - `GET /_debug/routes`
6. **Response headers** - `X-AI-Provider`, `X-Execution-Time`
7. **Security & isolation** - Sandboxing, rate limiting
8. **Streaming responses** - SSE for long-running tasks
