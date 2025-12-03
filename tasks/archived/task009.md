# Goal 

Support a dry-run option to skip AI agent execution and return the command that would have been executed. This is a **development-only feature** for debugging and testing purposes.

## How to Identify a Dry-Run Request

Dry-run mode can be activated through three sources with the following precedence order (highest to lowest):

### 1. Prompt File Configuration (Highest Priority)

Lock a prompt to always run in dry-run mode by adding to YAML frontmatter:

```yaml
---
dry: true
---
```

When `dry: true` is set in the prompt file, the prompt **always** runs in dry-run mode regardless of headers or query parameters.

### 2. HTTP Header (Medium Priority)

Header: `x-dry`

Truthy values (dry-run enabled):
- `x-dry` (header present with no value)
- `x-dry: true`
- `x-dry: 1`

Falsy values (dry-run disabled):
- `x-dry: false`
- `x-dry: 0`

### 3. Query String (Lowest Priority)

Parameter: `dry`

Truthy values (dry-run enabled):
- `?dry` (parameter present with no value)
- `?dry=true`
- `?dry=1`

Falsy values (dry-run disabled):
- `?dry=false`
- `?dry=0`

### Precedence Example

```
Prompt file: dry: true
Header: x-dry: false
Query: ?dry=false
→ Result: DRY-RUN (prompt file wins)

Prompt file: (not set)
Header: x-dry: true
Query: ?dry=false
→ Result: DRY-RUN (header wins)

Prompt file: (not set)
Header: (not set)
Query: ?dry=true
→ Result: DRY-RUN (query wins)
```

## How Dry-Run Mode Works

### Execution Flow

1. **Full Normal Processing**: Everything happens exactly as a real request:
   - Route matching (explicit routes and fallback)
   - Prompt file loading and YAML parsing
   - Variable substitution (path params, query params, body data)
   - Request body validation (if schema defined)
   - Provider availability checks
   - Workspace directory validation
   - All other pre-execution validation

2. **Command Construction**: Build the full AI agent command with:
   - Fully substituted prompt text
   - All variables resolved
   - Request body data merged into prompt
   - Model, agent mode, and other provider options applied

3. **Execution Bypass**: Instead of running the command via subprocess, return the command string

4. **Response**: Return the raw command as `text/plain` with HTTP 200

### Output Format

**Content-Type**: `text/plain`

**Body**: The exact shell command that would have been executed, as a single string.

Example output:
```
codex exec -m gpt-5.1-codex-mini "Generate a friendly greeting for Alice with role admin. Include a fun fact about their role."
```

The command string should be:
- Fully constructed with all arguments
- Ready to copy-paste into a terminal
- Include the complete prompt text with all variables substituted
- Show model overrides, agent mode flags, and any other provider-specific options

### Provider Implementation

Each `AIProvider` implementation must support dry-run mode:

1. **Add parameter** to `execute()` method:
   ```python
   def execute(self, prompt: str, model: str | None = None, agent: bool = False, dry_run: bool = False) -> AIProviderResult
   ```

2. **Command construction**: Build the full command as normal

3. **Conditional execution**:
   - If `dry_run=False`: Execute command via subprocess (current behavior)
   - If `dry_run=True`: Return the command string in `AIProviderResult.stdout`

4. **Result for dry-run**:
   ```python
   AIProviderResult(
       stdout=command_string,  # The full command as a string
       stderr="",
       returncode=0
   )
   ```

### Key Implementation Requirements

- **No shortcuts**: All validation, checks, and processing must run as normal
- **Provider checks**: Still verify provider is installed/available (show command even if it would fail)
- **Variable resolution**: Full substitution of all variables before command construction
- **Body handling**: Request body data must be merged into the prompt before building the command
- **Transparency**: The command output should reflect exactly what would execute in production

## Testing Strategy

### Unit Tests

Add basic dry-run tests to `test_providers.py`:
- Test `CodexProvider.execute()` with `dry_run=True`
- Verify command string is returned in `stdout`
- Verify `returncode=0` and `stderr=""` for dry-run
- Test with different models and agent mode combinations

### Integration Tests

Add tests to `test_main.py`:
- Test dry-run via query parameter: `GET /hi?dry=true`
- Test dry-run via header: `GET /hi` with `x-dry: true`
- Test dry-run with prompt that has variables and body data
- Verify response is `text/plain` with command string
- Verify HTTP 200 status

### E2E Tests

Add minimal test to `test_e2e.py`:
- Start real server
- Make request with dry-run enabled
- Verify command string is returned
- Verify no actual AI execution occurred

Keep tests simple - focus on verifying the command is constructed and returned correctly. Manual testing will cover edge cases.

## Future Enhancements (Not in Scope)

These are explicitly **NOT** part of this task but may be valuable later:

- Rich output showing execution context (workspace dir, timeout, model, matched prompt file)
- Structured JSON response format (command, args, context)
- Dry-run documentation in OpenAPI spec
- Separate logging/metrics for dry-run requests
- Command sanitization to hide sensitive paths/values