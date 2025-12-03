# Task 007 – OpenAPI Generation Plan

## Overview
Generate an OpenAPI 3.1 document on-demand at `/openapi.json` that lists endpoints derived from prompt files in `data/prompts/`. First iteration focuses on enumerating endpoints (routes + methods). Optionally include path parameters and request body schemas where defined by prompt frontmatter/body validator. Fail with a structured 500 error when validation or conflicts are detected. Feature gated via `OPENAPI_ENABLED`.

## Assumptions
- OpenAPI version: 3.1.
- Source of truth: prompt files in `data/prompts/` only.
- Dynamic routing parity: OpenAPI paths must mirror `router.py` logic.
- No caching: Generated per request.
- Optional request body: Only when defined in frontmatter/body validator.
- Env toggle: `OPENAPI_ENABLED` controls availability of `/openapi.json`.

## Architecture Touchpoints
- `src/prompts/loader.py`: Load prompt files and frontmatter.
- `src/prompts/router.py`: Resolve explicit routes and filename fallback.
- `src/prompts/body_validator.py`: Validate/structure request body configs.
- `src/main.py`: FastAPI app; add `/openapi.json` endpoint.
- New module: `src/openapi/generator.py`: Build OpenAPI document and validate conflicts.

## Potential Challenges & Mitigations
- Route conflicts (explicit vs filename fallback, overlapping patterns): implement deterministic conflict detection and full reporting.
- Schema correctness: align emitted JSON Schema with current validator to avoid drift.
- Parity with router: reuse router logic for path generation to avoid mismatch.
- Error reporting clarity: include file path, type, message, optional line numbers.

## Phases & Tasks

### Phase 1: Foundations
- Define config flag `OPENAPI_ENABLED` in `src/config.py` (default: true).
- Add new module `src/openapi/generator.py` with `generate_openapi()` and `validate_prompts()`.
- Decide disabled behavior: return 404 if disabled.

### Phase 2: Prompt Loading & Validation
- Use `loader.py` to load all prompts from `data/prompts/`.
- Validate frontmatter correctness (method, route pattern). Methods limited to supported set (e.g., GET initially).
- Detect conflicts:
  - Same method + exact path collision.
  - Explicit route collision with filename-based fallback.
  - Ambiguous path parameters (treat `/greet/{name}` vs `/greet/{id}` as conflict in v1).
- Collect all validation errors.

### Phase 3: OpenAPI Document Generation
- Build `info` section (title, version, description). Allow future env overrides.
- Build `paths` from router logic:
  - Path item per route.
  - Operation per method (likely `get` in v1).
  - `summary`/`description` from prompt metadata (optional).
  - Parameters: add path parameters as `in: path`, type `string` (v1 default).
  - Request body: include when body schema exists; convert validator structure to OpenAPI JSON Schema.
- Responses:
  - `200`: `text/plain` description (generic for v1).
  - Error responses: include standard entries (404, 500) with generic description.

### Phase 4: API Endpoint Wiring
- In `src/main.py`, add `/openapi.json` route:
  - Check `OPENAPI_ENABLED`; if false, return 404.
  - Call `generate_openapi()`; on validation errors, return 500 with structured error JSON.
  - On success, return OpenAPI JSON.

### Phase 5: Tests
- Unit tests (`tests/test_openapi_generator.py`):
  - Generation with valid prompts.
  - Conflict detection.
  - Body schema inclusion.
- Integration tests (`tests/test_main.py` updates):
  - `/openapi.json` returns document when enabled.
  - Returns 404 when disabled.
  - Returns 500 with structured errors on conflicts.
- E2E tests (`tests/test_e2e.py` updates):
  - Start server; GET `/openapi.json`; validate basic shape.
- Validate against OpenAPI (optionally use a validator library or schema check).

## Sequence of Actions
1. Add `OPENAPI_ENABLED` to config with default true.
2. Scaffold `src/openapi/generator.py` with core interfaces.
3. Implement prompt loading and conflict validation.
4. Implement OpenAPI building (info, paths, operations, parameters, requestBody, responses).
5. Wire endpoint in `src/main.py`; handle enabled/disabled and errors.
6. Write unit/integration/E2E tests; reuse fixtures in `tests/fixtures/prompts`.
7. Run test suites and adjust.

## Deliverables
- `src/openapi/generator.py` with `generate_openapi()` and validation helpers.
- `/openapi.json` route in `src/main.py` gated by `OPENAPI_ENABLED`.
- Structured error format for 500 responses on invalid prompts/conflicts.
- Tests covering generation, conflicts, env flag behavior.

## Test Checklist
- All tests pass: `pytest tests/ -v`.
- Unit:
  - Valid prompts produce OpenAPI paths.
  - Conflicts detected and reported.
  - Request body emitted when frontmatter defines it.
- Integration:
  - `/openapi.json` enabled path returns JSON.
  - Disabled returns 404.
  - Conflicts yield 500 with error list.
- E2E:
  - Server returns valid JSON document; includes known endpoints (`/hi`, `/greet/{name}`).

## Try It Commands
```zsh
# Run all tests
pytest tests/ -v

# Start dev server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Fetch openapi
curl -s http://localhost:8000/openapi.json | jq '.'
```
