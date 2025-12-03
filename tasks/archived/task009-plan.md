# Task 009: Dry-Run Mode - Implementation Plan

## Overview

Implement dry-run mode to skip AI agent execution and return the command that would have been executed. This is a development-only debugging feature that follows the full request processing pipeline but bypasses actual subprocess execution.

**Task ID**: task009  
**Complexity**: Medium  
**Estimated Effort**: 4-6 hours  

---

## Architecture Analysis

### Current System Touchpoints

The dry-run feature will integrate into these existing components:

1. **`src/prompts/loader.py`**: `PromptMetadata` dataclass
   - Add `dry` field to store prompt-level dry-run configuration

2. **`src/providers/base.py`**: `AIProvider` abstract class
   - Add `dry_run` parameter to `execute()` method signature

3. **`src/providers/codex.py`**: `CodexProvider` implementation
   - Implement dry-run logic to construct and return command string

4. **`src/prompts/executor.py`**: `PromptExecutor` class
   - Pass dry-run flag from request to provider

5. **`src/main.py`**: Dynamic route handler
   - Extract dry-run flag from query/header
   - Apply precedence logic (prompt → header → query)
   - Pass dry-run flag through execution chain

### Dependencies

- No new external dependencies required
- All changes within existing modules
- Backward compatible (dry-run defaults to `False`)

---

## Implementation Phases

### Phase 1: Data Model Updates

**Goal**: Add dry-run support to data structures

#### Task 1.1: Update `PromptMetadata`
**File**: `src/prompts/loader.py`

**Changes**:
- Add `dry: bool | None = None` field to `PromptMetadata` dataclass
- Extract `dry` from YAML frontmatter in `load_prompts()` function
- Parse as boolean (same logic as `agent` field)

**Acceptance Criteria**:
- Prompts can have `dry: true` in frontmatter
- Field defaults to `None` when not specified
- YAML parsing handles both boolean and string values

#### Task 1.2: Update `AIProvider` Abstract Class
**File**: `src/providers/base.py`

**Changes**:
- Add `dry_run: bool = False` parameter to `execute()` abstract method signature
- Update docstring to document dry-run behavior

**Acceptance Criteria**:
- All provider implementations must support `dry_run` parameter
- Default value is `False` (normal execution)
- Method signature is backward compatible

---

### Phase 2: Provider Implementation

**Goal**: Implement dry-run logic in CodexProvider

#### Task 2.1: Add Dry-Run to `CodexProvider`
**File**: `src/providers/codex.py`

**Changes**:
1. Update `execute()` signature to accept `dry_run: bool = False`
2. Move command construction logic before execution check
3. Add conditional: if `dry_run=True`, return command string
4. Return `AIProviderResult` with:
   - `stdout`: Full command string (ready to copy-paste)
   - `stderr`: Empty string
   - `returncode`: 0
   - `success`: True

**Command String Format**:
```python
# Example output:
"codex exec --sandbox workspace-write --model gpt-5.1-codex-mini \"Your prompt here\""
```

**Acceptance Criteria**:
- Command string includes all arguments in correct order
- Prompt text is properly quoted for shell execution
- Model overrides are reflected in command
- Provider availability checks still run (return command even if would fail)
- Dry-run bypasses subprocess execution entirely

---

### Phase 3: Request Processing

**Goal**: Extract and propagate dry-run flag through request pipeline

#### Task 3.1: Add Dry-Run Detection in Main Handler
**File**: `src/main.py`

**Changes in `dynamic_prompt_handler()`**:

1. **Extract dry-run from query parameter** (after path extraction):
   ```python
   # Get dry-run from query parameter (lowest priority)
   dry_from_query = request.query_params.get('dry')
   dry_query = _parse_dry_flag(dry_from_query)
   ```

2. **Extract dry-run from header** (after user/project headers):
   ```python
   # Get dry-run from header (medium priority)
   dry_from_header = request.headers.get('x-dry')
   dry_header = _parse_dry_flag(dry_from_header)
   ```

3. **Apply precedence logic** (after prompt matching):
   ```python
   # Determine final dry-run value (prompt > header > query)
   dry_run = match.prompt.dry if match.prompt.dry is not None else (
       dry_header if dry_header is not None else (
           dry_query if dry_query is not None else False
       )
   )
   ```

4. **Add helper function** (top of file, after imports):
   ```python
   def _parse_dry_flag(value: str | None) -> bool | None:
       """Parse dry-run flag from query/header value."""
       if value is None:
           return None
       if value == "":  # Header present with no value
           return True
       normalized = value.lower()
       if normalized in ("true", "1"):
           return True
       if normalized in ("false", "0"):
           return False
       return None  # Invalid value treated as not set
   ```

**Acceptance Criteria**:
- Query parameter `?dry`, `?dry=true`, `?dry=1` enable dry-run
- Query parameter `?dry=false`, `?dry=0` disable dry-run
- Header `x-dry`, `x-dry: true`, `x-dry: 1` enable dry-run
- Header `x-dry: false`, `x-dry: 0` disable dry-run
- Precedence order respected: prompt → header → query → default (false)
- Invalid values treated as not set (use next priority level)

#### Task 3.2: Update Executor Call
**File**: `src/main.py`

**Changes in `dynamic_prompt_handler()`**:
- Pass `dry_run` flag to executor (modify executor.execute() call)

**Note**: Requires updating `PromptExecutor.execute()` to accept and pass through dry-run flag

---

### Phase 4: Executor Updates

**Goal**: Pass dry-run flag from executor to provider

#### Task 4.1: Update `PromptExecutor.execute()`
**File**: `src/prompts/executor.py`

**Changes**:
1. Add `dry_run: bool = False` parameter to `execute()` method
2. Pass `dry_run` to provider's `execute()` call

**Updated signature**:
```python
def execute(
    self,
    prompt: PromptMetadata,
    route_params: dict[str, str] | None = None,
    body_params: dict[str, str] | None = None,
    dry_run: bool = False,
) -> AIProviderResult:
```

**Changes in execution**:
```python
# Execute with dry-run flag
if prompt.model:
    result = provider.execute(processed_prompt, model=prompt.model, dry_run=dry_run)
else:
    result = provider.execute(processed_prompt, dry_run=dry_run)
```

**Acceptance Criteria**:
- Dry-run flag propagates from handler → executor → provider
- All validation and processing runs normally
- Only subprocess execution is skipped

---

### Phase 5: Testing

**Goal**: Validate dry-run implementation with comprehensive tests

#### Task 5.1: Unit Tests - Provider Layer
**File**: `tests/test_providers.py`

**New Tests**:
```python
class TestCodexProviderDryRun:
    def test_dry_run_returns_command_string(self, tmp_path):
        """Dry-run returns command without execution"""
        
    def test_dry_run_with_model_override(self, tmp_path):
        """Dry-run includes model in command"""
        
    def test_dry_run_with_default_model(self, tmp_path):
        """Dry-run uses default model when not specified"""
        
    def test_dry_run_success_indicators(self, tmp_path):
        """Dry-run returns success=True, returncode=0, stderr empty"""
```

**Acceptance Criteria**:
- Command string matches expected format
- Model overrides reflected correctly
- Result object has correct success indicators
- No subprocess execution occurs

#### Task 5.2: Integration Tests - API Layer
**File**: `tests/test_main.py`

**New Tests**:
```python
def test_dry_run_via_query_parameter():
    """GET /hi?dry=true returns command string"""
    
def test_dry_run_via_header():
    """GET /hi with x-dry: true returns command string"""
    
def test_dry_run_precedence_prompt_over_header():
    """Prompt-level dry wins over header"""
    
def test_dry_run_precedence_header_over_query():
    """Header dry wins over query parameter"""
    
def test_dry_run_with_variables_substituted():
    """Dry-run shows fully substituted prompt"""
    
def test_dry_run_disabled_via_query():
    """?dry=false executes normally"""
```

**Acceptance Criteria**:
- Response is `text/plain` with command string
- HTTP 200 status for successful dry-run
- Variable substitution visible in command
- Precedence logic works correctly

#### Task 5.3: E2E Tests - Real Server
**File**: `tests/test_e2e.py`

**New Tests**:
```python
def test_e2e_dry_run_basic():
    """E2E: Dry-run returns command, no execution"""
```

**Acceptance Criteria**:
- Real HTTP server returns command string
- No actual AI execution occurs
- Response matches expected format

---

## Potential Challenges & Solutions

### Challenge 1: Command String Escaping
**Problem**: Shell special characters in prompt text need proper escaping

**Solution**: 
- Use Python's `shlex.quote()` for proper shell escaping
- Test with prompts containing quotes, newlines, special chars

### Challenge 2: Multi-line Prompts
**Problem**: Prompts with newlines need proper formatting in command string

**Solution**:
- Keep prompt as single string argument
- Shell quoting handles newlines automatically
- Display command as-is (copy-pasteable)

### Challenge 3: Precedence Edge Cases
**Problem**: Multiple sources might conflict

**Solution**:
- Clear precedence order: prompt → header → query → default
- Invalid values treated as "not set" (fall through to next level)
- Document behavior in task description

### Challenge 4: Provider Availability
**Problem**: Should dry-run check if provider is installed?

**Solution**:
- Yes, run all checks as normal execution would
- Return command string even if provider unavailable
- This helps debug installation issues

---

## Testing Checklist

### Unit Tests
- [ ] `PromptMetadata` parses `dry` field from YAML
- [ ] `CodexProvider.execute()` with `dry_run=True` returns command
- [ ] Command string includes model override
- [ ] Command string includes default model
- [ ] Dry-run result has `success=True`, `returncode=0`, `stderr=""`
- [ ] Command string is properly quoted/escaped

### Integration Tests
- [ ] `GET /hi?dry=true` returns command string
- [ ] `GET /hi?dry=false` executes normally
- [ ] `GET /hi` with `x-dry: true` returns command
- [ ] `GET /hi` with `x-dry: false` executes normally
- [ ] Prompt with `dry: true` always returns command
- [ ] Precedence: prompt > header works
- [ ] Precedence: header > query works
- [ ] Variable substitution visible in dry-run output
- [ ] Response is `text/plain`
- [ ] HTTP 200 status for dry-run

### E2E Tests
- [ ] Real server returns command string
- [ ] No actual subprocess execution
- [ ] Can copy-paste command and run manually

### Manual Testing
- [ ] Test with multi-line prompts
- [ ] Test with special characters in prompt
- [ ] Test with body data substitution
- [ ] Test with path parameters
- [ ] Verify command is copy-pasteable to terminal

---

## Deliverables

### Code Changes
1. ✅ Updated `src/prompts/loader.py` - Add `dry` field to `PromptMetadata`
2. ✅ Updated `src/providers/base.py` - Add `dry_run` parameter to abstract method
3. ✅ Updated `src/providers/codex.py` - Implement dry-run logic
4. ✅ Updated `src/prompts/executor.py` - Pass dry-run flag to provider
5. ✅ Updated `src/main.py` - Extract dry-run, apply precedence, pass to executor
6. ✅ Added helper function `_parse_dry_flag()` in `src/main.py`

### Tests
1. ✅ Unit tests in `tests/test_providers.py` (4 new tests)
2. ✅ Integration tests in `tests/test_main.py` (7 new tests)
3. ✅ E2E test in `tests/test_e2e.py` (1 new test)

### Documentation
1. ✅ Updated task description with implementation details
2. ✅ Code comments in modified functions
3. ✅ Docstring updates for new parameters

---

## Validation Criteria

### Functional Requirements
- [ ] Dry-run can be enabled via query parameter, header, or prompt file
- [ ] Precedence order is respected (prompt > header > query)
- [ ] Command string is fully constructed with all substitutions
- [ ] Command string is copy-pasteable to terminal
- [ ] Response is `text/plain` with HTTP 200
- [ ] All validation/processing runs normally (only execution skipped)

### Non-Functional Requirements
- [ ] No performance impact on normal requests
- [ ] Backward compatible (no breaking changes)
- [ ] Code is maintainable and well-documented
- [ ] Test coverage for all dry-run paths

### Quality Gates
- [ ] All existing tests pass
- [ ] All new tests pass
- [ ] No lint errors
- [ ] Manual testing completed successfully

---

## Execution Sequence

1. **Phase 1** (30 min): Update data models
   - Task 1.1: `PromptMetadata` field
   - Task 1.2: `AIProvider` signature

2. **Phase 2** (60 min): Implement provider dry-run
   - Task 2.1: `CodexProvider` logic

3. **Phase 3** (45 min): Request processing
   - Task 3.1: Extract and apply precedence
   - Task 3.2: Update executor call

4. **Phase 4** (30 min): Executor updates
   - Task 4.1: Pass dry-run to provider

5. **Phase 5** (90 min): Testing
   - Task 5.1: Unit tests
   - Task 5.2: Integration tests
   - Task 5.3: E2E tests

6. **Validation** (30 min): Manual testing and verification

**Total Estimated Time**: 4.5 hours

---

## Success Metrics

✅ **Implementation Complete** when:
- All code changes merged
- All tests passing (including existing tests)
- Manual testing confirms command is copy-pasteable
- Documentation updated

✅ **Feature Working** when:
- `GET /hi?dry=true` returns command string
- Command can be run manually in terminal
- Dry-run respects all precedence rules
- Variable substitution works in dry-run mode

---

## Notes

- This is a **development-only** feature - no production concerns
- Future enhancements (rich output, JSON format) explicitly out of scope
- Keep implementation simple and focused on core functionality
- Dry-run should feel like "preview before execution"
