# Task 005 Execution Plan: Request Body Validation

## Overview
Implement request body validation for POST/PUT/PATCH endpoints using Pydantic with OpenAPI-compatible schema definitions. This plan breaks down the implementation into clear phases with specific tasks and validates against the existing codebase architecture.

## Current Codebase Analysis

### Existing Components
- **src/prompts/loader.py**: Parses YAML frontmatter using `python-frontmatter`, creates `PromptMetadata`
- **src/prompts/variables.py**: Handles `${variable}` and `${variable:default}` substitution with regex
- **src/prompts/executor.py**: Executes prompts with AI provider, calls variable substitution
- **src/prompts/router.py**: Matches routes (explicit and fallback), extracts path parameters
- **src/main.py**: FastAPI app with dynamic route handler, error handling with HTTPException
- **requirements.txt**: Already has `pydantic==2.12.5` installed ✅

### Key Integration Points
1. **PromptMetadata** needs new `body_schema` field
2. **Variable substitution** needs to support `${route.x}` and `${body.x}` syntax
3. **Executor** needs to validate body before execution
4. **Main.py** needs to extract request body and pass to executor
5. **Router** needs to validate body schema doesn't conflict with route params

---

## Phase 1: Foundation & Schema Definition

### Task 1.1: Create Body Validator Module
**File**: `src/prompts/body_validator.py`

**Deliverables**:
- [ ] `BodyFieldSchema` dataclass to represent a field definition
  - Properties: `name`, `type`, `required`, `default`, `description`, `minLength`, `maxLength`, `min`, `max`, `maxDecimals`, `pattern`, `enum`
- [ ] `parse_body_schema()` function to parse frontmatter body section into list of `BodyFieldSchema`
- [ ] `validate_body_schema()` function to check for configuration errors (duplicate names, invalid regex, invalid enum)
- [ ] Unit tests in `tests/test_body_validator.py` for schema parsing

**Dependencies**: None

**Estimated complexity**: Medium

---

### Task 1.2: Update PromptMetadata
**File**: `src/prompts/loader.py`

**Deliverables**:
- [ ] Add `body_schema: dict[str, Any] | None` field to `PromptMetadata` dataclass
- [ ] Update `load_prompts()` to extract `body` from frontmatter metadata
- [ ] Add logging for loaded body schemas

**Dependencies**: None

**Estimated complexity**: Low

---

### Task 1.3: Schema Validation Logic
**File**: `src/prompts/body_validator.py`

**Deliverables**:
- [ ] `build_pydantic_model()` function to create dynamic Pydantic model from `BodyFieldSchema` list
  - Use `pydantic.create_model()` for dynamic creation
  - Support `string`, `number`, `boolean` types
  - Apply validation constraints (min/max, minLength/maxLength, pattern, enum)
  - Handle `maxDecimals` for number fields using custom validator
  - Set default values properly
- [ ] `ValidationError` custom exception for configuration errors
- [ ] Unit tests for Pydantic model generation with all field types

**Dependencies**: Task 1.1

**Estimated complexity**: High

---

## Phase 2: Variable System Enhancement

### Task 2.1: Update Variable Substitution Pattern
**File**: `src/prompts/variables.py`

**Deliverables**:
- [ ] Update regex pattern to match `${route.name}`, `${body.name}`, and `${body.name:default}`
- [ ] Modify `substitute_variables()` to accept two separate dicts: `route_params` and `body_params`
- [ ] Handle namespaced substitution properly (route. and body. prefixes)
- [ ] Maintain backward compatibility for simple `${name}` syntax (deprecate in logs)
- [ ] Add comprehensive unit tests for new syntax

**Dependencies**: None

**Estimated complexity**: Medium

**Breaking change**: Yes, but backward compatible with warnings

---

### Task 2.2: Update Executor for New Variable System
**File**: `src/prompts/executor.py`

**Deliverables**:
- [ ] Update `execute()` signature to accept `body_params: dict[str, Any]`
- [ ] Update call to `substitute_variables()` with both `route_params` and `body_params`
- [ ] Add logging for body parameter substitution

**Dependencies**: Task 2.1

**Estimated complexity**: Low

---

## Phase 3: Request Body Validation

### Task 3.1: Implement Body Validation Function
**File**: `src/prompts/body_validator.py`

**Deliverables**:
- [ ] `validate_request_body()` function
  - Input: raw JSON body, Pydantic model
  - Output: validated data dict or list of validation errors
  - Collect ALL validation errors (not fail-fast)
  - Handle missing required fields, type mismatches, constraint violations, extra fields
- [ ] `format_validation_errors()` function to convert Pydantic errors to API error format
  - Structure: field path, error message, received value, expected description
  - Add helpful suggestions for common errors
- [ ] Unit tests for validation scenarios

**Dependencies**: Task 1.3

**Estimated complexity**: High

---

### Task 3.2: Configuration Validation
**File**: `src/prompts/body_validator.py`

**Deliverables**:
- [ ] `validate_prompt_configuration()` function
  - Check verb is POST/PUT/PATCH when body schema exists
  - Check no duplicate field names between route params and body fields
  - Check regex patterns are valid
  - Check enum values are non-empty lists
  - Return configuration error details
- [ ] Unit tests for configuration validation

**Dependencies**: Task 1.2, Task 1.3

**Estimated complexity**: Medium

---

## Phase 4: Integration with FastAPI

### Task 4.1: Update Main Handler for Body Processing
**File**: `src/main.py`

**Deliverables**:
- [ ] Extract request body in `dynamic_prompt_handler()`
  - Check Content-Type header (must be `application/json`)
  - Return `415 Unsupported Media Type` for non-JSON
  - Parse JSON body with error handling
- [ ] Add body validation step after route matching
  - Check if prompt has body schema
  - Validate configuration (verb, duplicate fields)
  - Return `500 Internal Server Error` for config issues
  - Validate request body against schema
  - Return `422 Unprocessable Entity` for validation errors
- [ ] Pass validated body to executor
- [ ] Update error handling for new error types

**Dependencies**: Task 3.1, Task 3.2

**Estimated complexity**: High

---

### Task 4.2: Update Error Response Format
**File**: `src/main.py`

**Deliverables**:
- [ ] Create standardized error response helper function
- [ ] Implement `422 Unprocessable Entity` response format
  - Include field-level errors with details
  - Add resolution hints
- [ ] Implement `415 Unsupported Media Type` response
- [ ] Update `500 Internal Server Error` for configuration errors
  - Include file path, error message, resolution
- [ ] Update existing error handlers to use new format

**Dependencies**: Task 4.1

**Estimated complexity**: Medium

---

## Phase 5: Testing

### Task 5.1: Unit Tests for Body Validator
**File**: `tests/test_body_validator.py`

**Test scenarios**:
- [ ] Parse body schema from YAML correctly
- [ ] Build Pydantic models for all type combinations
- [ ] Validate string fields (minLength, maxLength, pattern, enum)
- [ ] Validate number fields (min, max, maxDecimals)
- [ ] Validate boolean fields
- [ ] Apply default values when fields missing
- [ ] Reject extra fields
- [ ] Collect multiple validation errors
- [ ] Detect configuration errors (verb mismatch, duplicate fields, invalid regex)
- [ ] Format validation errors correctly

**Dependencies**: Phase 3

**Estimated complexity**: High

---

### Task 5.2: Integration Tests
**File**: `tests/test_main.py`

**Test scenarios**:
- [ ] POST with valid body returns success
- [ ] POST with invalid body returns 422 with error details
- [ ] POST with missing required fields returns 422
- [ ] POST with extra fields returns 422
- [ ] POST without Content-Type application/json returns 415
- [ ] POST with malformed JSON returns 400
- [ ] GET with body schema returns 500 (config error)
- [ ] POST with duplicate field names returns 500 (config error)
- [ ] Body variable substitution works correctly

**Dependencies**: Phase 4

**Estimated complexity**: Medium

---

### Task 5.3: E2E Tests with Test Prompts
**File**: `tests/test_e2e.py` + test prompt files

**Test prompts to create** (all under `/test/` routes):

1. **`data/prompts/test-body-simple.md`**
   ```yaml
   route: /test/body-simple
   verb: POST
   body:
     message:
       type: string
       required: true
   ```

2. **`data/prompts/test-body-validation.md`**
   ```yaml
   route: /test/body-validation
   verb: POST
   body:
     age:
       type: number
       min: 0
       max: 120
       maxDecimals: 0
     email:
       type: string
       pattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
   ```

3. **`data/prompts/test-body-defaults.md`**
   ```yaml
   route: /test/body-defaults
   verb: POST
   body:
     name:
       type: string
       default: Anonymous
     active:
       type: boolean
       default: true
   ```

4. **`data/prompts/test-body-enum.md`**
   ```yaml
   route: /test/body-enum
   verb: POST
   body:
     color:
       type: string
       enum: [red, green, blue]
       required: true
   ```

5. **`data/prompts/test-body-errors.md`** (for testing multiple errors)
   ```yaml
   route: /test/body-errors
   verb: POST
   body:
     field1:
       type: string
       required: true
       minLength: 5
     field2:
       type: number
       required: true
       min: 1
       max: 10
   ```

6. **`data/prompts/test-body-config-error.md`** (for testing config validation)
   ```yaml
   route: /test/body-config-error/{name}
   verb: POST
   body:
     name:  # Duplicate with route param
       type: string
   ```

**Test cases**:
- [ ] Valid requests return 200 with AI response
- [ ] Invalid bodies return 422 with detailed errors
- [ ] Missing required fields caught
- [ ] Boundary violations detected (min/max, length)
- [ ] Pattern matching works
- [ ] Enum validation works
- [ ] Default values applied
- [ ] Multiple errors collected
- [ ] Configuration errors return 500
- [ ] Content-Type validation works

**Dependencies**: Phase 4

**Estimated complexity**: High

---

## Phase 6: Documentation & Cleanup

### Task 6.1: Update copilot-instructions.md
**File**: `.github/copilot-instructions.md`

**Deliverables**:
- [ ] Document body schema syntax
- [ ] Add examples of body validation
- [ ] Update variable substitution documentation
- [ ] Document error responses
- [ ] Add troubleshooting section

**Dependencies**: Phase 5 (after implementation verified)

**Estimated complexity**: Low

---

### Task 6.2: Final Testing & Validation
**Deliverables**:
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify all tests pass
- [ ] Check test coverage for new modules
- [ ] Manual testing with curl commands
- [ ] Validate error messages are helpful
- [ ] Check logging output is appropriate

**Dependencies**: Phase 5

**Estimated complexity**: Low

---

## Risk Assessment & Mitigation

### Potential Challenges

1. **Pydantic Dynamic Model Creation Complexity**
   - **Risk**: Complex validation rules may not map cleanly to Pydantic
   - **Mitigation**: Start with basic validation, add custom validators as needed
   - **Fallback**: Implement manual validation if Pydantic proves limiting

2. **Variable Syntax Breaking Changes**
   - **Risk**: Existing prompts may break with new syntax
   - **Mitigation**: Maintain backward compatibility, add deprecation warnings
   - **Fallback**: Support both old and new syntax with feature flag

3. **Error Message Complexity**
   - **Risk**: Pydantic errors may be too technical for users
   - **Mitigation**: Create custom error formatter with user-friendly messages
   - **Fallback**: Provide both technical and simplified error formats

4. **Regex Pattern Validation**
   - **Risk**: Invalid regex in frontmatter could crash the app
   - **Mitigation**: Validate regex patterns during prompt loading, return 500 for bad config
   - **Fallback**: Catch regex errors and return helpful error messages

5. **MaxDecimals Implementation**
   - **Risk**: Pydantic doesn't have built-in decimal precision validation
   - **Mitigation**: Use custom validator with `@field_validator` decorator
   - **Fallback**: Manual post-validation check

---

## Implementation Order

1. **Phase 1** → Foundation (Tasks 1.1, 1.2, 1.3)
2. **Phase 2** → Variables (Tasks 2.1, 2.2)
3. **Phase 3** → Validation (Tasks 3.1, 3.2)
4. **Phase 4** → Integration (Tasks 4.1, 4.2)
5. **Phase 5** → Testing (Tasks 5.1, 5.2, 5.3)
6. **Phase 6** → Documentation (Tasks 6.1, 6.2)

**Recommended approach**: Implement one phase completely before moving to next, run tests after each phase.

---

## Final Deliverables Checklist

### Code Deliverables
- [ ] `src/prompts/body_validator.py` - Complete module with all validation logic
- [ ] Updated `src/prompts/loader.py` - Parse body schema from frontmatter
- [ ] Updated `src/prompts/variables.py` - Support namespaced variables
- [ ] Updated `src/prompts/executor.py` - Pass body params to substitution
- [ ] Updated `src/main.py` - Handle body validation and errors
- [ ] `requirements.txt` - Pydantic already present ✅

### Test Deliverables
- [ ] `tests/test_body_validator.py` - Comprehensive unit tests
- [ ] Updated `tests/test_main.py` - Integration tests for body handling
- [ ] Updated `tests/test_e2e.py` - E2E tests with real server
- [ ] 6 test prompt files in `data/prompts/` (test-body-*.md)
- [ ] All existing tests still pass
- [ ] New tests achieve >90% coverage of new code

### Documentation Deliverables
- [ ] Updated `.github/copilot-instructions.md`
- [ ] Code comments and docstrings
- [ ] Example prompts demonstrating features

### Validation Deliverables
- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] Manual curl testing successful
- [ ] Error messages verified for clarity
- [ ] Logging output reviewed
- [ ] No breaking changes to existing functionality

---

## Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_body_validator.py -v        # Unit tests
pytest tests/test_main.py -v                  # Integration tests
pytest tests/test_e2e.py -v                   # E2E tests

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Manual testing examples
curl -X POST http://localhost:8000/test/body-simple \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

curl -X POST http://localhost:8000/test/body-validation \
  -H "Content-Type: application/json" \
  -d '{"age": 25, "email": "test@example.com"}'

# Test validation errors
curl -X POST http://localhost:8000/test/body-errors \
  -H "Content-Type: application/json" \
  -d '{"field1": "hi", "field2": 100}'  # Should return 422

# Test Content-Type validation
curl -X POST http://localhost:8000/test/body-simple \
  -d 'message=hello'  # Should return 415
```

---

## Success Criteria

1. ✅ Pydantic models created dynamically from YAML frontmatter
2. ✅ All three types (string, number, boolean) supported with validation
3. ✅ Validation constraints enforced (min/max, length, pattern, enum, maxDecimals)
4. ✅ Default values applied when fields missing
5. ✅ Multiple validation errors collected and returned
6. ✅ Configuration errors detected and return 500
7. ✅ Content-Type validation enforces JSON
8. ✅ Variable syntax supports `${route.x}` and `${body.x}`
9. ✅ Comprehensive error messages with resolution hints
10. ✅ All tests pass including E2E tests
11. ✅ No breaking changes to existing functionality
12. ✅ Code follows SRP and is modular

---

## Estimated Time

- **Phase 1**: 3-4 hours
- **Phase 2**: 2-3 hours
- **Phase 3**: 4-5 hours
- **Phase 4**: 3-4 hours
- **Phase 5**: 5-6 hours
- **Phase 6**: 1-2 hours

**Total**: 18-24 hours of development time

---

## Notes

- Pydantic is already in requirements.txt (v2.12.5), no installation needed
- Existing architecture is well-suited for this enhancement
- No database changes required
- No deployment changes required
- Feature can be developed and tested locally
- Backward compatible with existing prompts (those without body schemas)
