# Goal

Run interfaces to stored prompts.

## Preconditions

The project has a configurable data folder (defaults to ./data).
This document refers to this folder as "data folder" or "user data" or "data sandbox"

The project has a configurable AI environment (defaults to codex) that can execute prompts.
This document refers to this folder as "AI" or "the AI" or "ai cli".

## API Surface

The server should accept requests on any kind of api sub-path and http verb.
The validity of the request will be checked against a library of prompts.

## Prompts Library

When executing a request, the first thing to do is to load the available prompts from `data/prompts/*.md`.
In this step, you should only fetch the frontmatter of the prompts so to build an array of possible configurations.

Each item in this list should contain:
- fileName (without extension)
- filePath (full path to the prompt file)
- config (the parsed frontmatter)

**Debugging Output:** Print this list to the terminal for debugging purposes using structured logging.

## Matching a Route

Each prompt can define 2 properties that impact the path definition:
- `verb`: any supported HTTP verb such as GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS (defaults to GET if not specified)
- `route`: path pattern definition using FastAPI syntax such as: `/foo` or `/user/{name}` or `/files/{path:path}`

**Route Matching Strategy:**

The request handler should use FastAPI's native routing capabilities with dynamic route registration.

### Primary Match (Explicit Routes)
1. First scan all prompts with explicit `route` configuration
2. Match against `verb` + `route` pattern
3. If match found, use that prompt

### Fallback Match (Filename-based Routes)
1. If no explicit route matches, scan all prompts by filename
2. Generate implicit route: `GET /{fileName}` (filename without `.md` extension)
3. Example: `hi.md` → `GET /hi`, `calc.md` → `GET /calc`
4. If match found, use that prompt

### No Match
- Return HTTP 404 with proper error message
- Error should indicate no matching prompt was found for the requested path and method

**Route Priority:** First match wins (file system order). If multiple prompts define the same route+verb, the first one loaded will be used.

**Debugging Output:** Print the matching prompt filename and match solution (explicit vs fallback) to the terminal for debugging.

## Route Implementation

1. Read the full content of the matched prompt file
2. Parse and extract the prompt body (content after frontmatter)
3. Perform variable substitution on the prompt body (see below)
4. Execute the AI provider with the processed prompt
5. Return the raw stdout from the AI provider as plain text response (Content-Type: text/plain)

**Response Format:** Return raw AI provider stdout without any processing, cleaning, or parsing. Include all output exactly as the AI returns it.

## Error Handling

### AI Provider Errors
- **Timeout (returncode 124):** HTTP 408 Request Timeout with error details
- **Execution failure:** HTTP 500 Internal Server Error with returncode and stderr
- **Provider unavailable:** HTTP 503 Service Unavailable with provider name
- **Provider not found:** HTTP 503 Service Unavailable with list of available providers

### Route Errors
- **No matching route:** HTTP 404 Not Found with descriptive message
- **Prompt file not found/unreadable:** HTTP 500 Internal Server Error

### Malformed Prompts
**Deferred:** Frontmatter validation is not implemented in this phase. Invalid frontmatter should be handled gracefully (skip invalid fields, use defaults). This will be addressed in a future task.

## Prompt Configuration (Frontmatter)

A prompt document can expose different configurations in the frontmatter (YAML format):

### Implemented Fields

#### `verb` (string, optional)
HTTP method for the route. Defaults to `GET`.
Valid values: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
Example: `verb: POST`

#### `route` (string, optional)
Path pattern using FastAPI syntax. If not specified, defaults to `/{filename}` where filename is the prompt file name without extension.
Example: `route: /user/{name}/profile`

#### `model` (string, optional)
LLM model to use with the AI provider. Overrides the global configuration.
Example: `model: gpt-5.1-codex-mini`

#### `agent` (string, optional)
Which agentic platform to use (e.g., "codex", "claude-code", "copilot"). Overrides the global AI_PROVIDER configuration.
Example: `agent: codex`

### Future Fields (Not Implemented)
**Deferred to future tasks:**
- `timeout`: Per-prompt timeout override
- `workspace_dir`: Isolated sandbox directory
- `sandbox_permissions`: Codex CLI sandbox flags
- Other codex CLI flags (`--search`, `--full-auto`, etc.)

## Variable Substitution

### Syntax
Use bash-style variable syntax: `${variable}` or `${variable:default_value}`

Examples:
- `${name}` - Simple variable substitution
- `${role:guest}` - Variable with default value "guest"
- `Hello ${name}! Your role is ${role:user}.`

### Variable Sources (Current Phase)
- **Path parameters:** Extracted from route pattern
  - Route: `/user/{name}` → Request: `/user/john` → `${name}` = "john"
  - Route: `/api/{version}/resource/{id}` → `${version}`, `${id}` available

### Variable Sources (Future Phases)
**Deferred to next task:**
- Query parameters (e.g., `?role=admin`)
- Request body (POST/PUT data)
- Headers
- Environment variables

### Implementation
Use Python's string Template or similar for substitution. If a variable is not found and has no default, substitute with empty string (graceful degradation).

### Example Prompt
```markdown
---
route: /greet/{name}
verb: GET
model: gpt-5.1-codex-mini
---

Generate a personalized greeting for ${name} with the role of ${role:guest}.
```

Request: `GET /greet/Alice` → Prompt: "Generate a personalized greeting for Alice with the role of guest."

## Prompt Loading Strategy

**Load on every request.** Performance is not a concern for this phase.

Each request should:
1. Scan `data/prompts/*.md` directory
2. Parse frontmatter from each file
3. Build routing table
4. Match request
5. Load and execute matched prompt

This allows dynamic prompt updates without server restart.

**Future optimization:** Caching with file watcher will be addressed in a later task.

## Debugging & Observability

### Logging Requirements
- Log prompt library (list of loaded prompts with config) at DEBUG level
- Log matched prompt and match type (explicit vs fallback) at INFO level
- Log AI provider execution details (stdout, stderr, returncode) at DEBUG level
- Log errors with full context at ERROR level

### Debug Endpoint (Future)
**Deferred:** A `GET /_debug/routes` endpoint to inspect loaded prompts and routing table will be implemented in a future task.

### Response Headers (Future)
**Deferred:** Consider adding informational headers in future:
- `X-AI-Provider: codex`
- `X-AI-Model: gpt-5.1-codex-mini`
- `X-Execution-Time: 1234ms`
- `X-Prompt-File: calc.md`

## Backward Compatibility

**Existing endpoints (`/hello`, `/test-write`) must continue to work.**

### Priority Order
1. Static routes defined in code (FastAPI routes in `main.py`)
2. Dynamic prompt-based routes (explicit `route` configuration)
3. Fallback filename-based routes

This ensures existing functionality is not broken by the new dynamic routing system.

**Future migration:** Consider moving existing endpoints to prompt-based system in a later task.

## Security & Isolation

**Security is not a concern for this phase.** 

- No sandboxing between prompts
- Prompts can access files created by other prompts
- No directory access restrictions
- No rate limiting
- All prompts share the same workspace directory

**Future considerations:** Implement proper isolation, rate limiting, and security controls in production deployment.

## Testing Requirements

Per project guidelines, **tests must be run after any code changes.**

### Required Tests
1. **Unit tests for prompt loading:**
   - Parse frontmatter correctly
   - Handle missing frontmatter fields
   - Handle malformed files gracefully

2. **Unit tests for route matching:**
   - Match explicit routes
   - Match fallback filename routes
   - Handle no match (404)
   - Test variable extraction from path

3. **Unit tests for variable substitution:**
   - Simple variables
   - Variables with defaults
   - Missing variables
   - Multiple variables

4. **E2E tests:**
   - Full request flow with sample prompts
   - Different HTTP verbs
   - Path parameters
   - Error scenarios (404, 500, 503)

5. **Mock AI provider:**
   - Use mocked provider in unit tests
   - Real provider in E2E tests (optional)

### Test Fixtures
Create sample prompts in `tests/fixtures/prompts/`:
- Simple prompt without frontmatter
- Prompt with explicit route and verb
- Prompt with path parameters
- Prompt with model override

Run tests with: `pytest tests/ -v`

## Implementation Notes

### Routing Library Choice
**Use FastAPI's native routing with dynamic route registration.**

FastAPI supports:
- Path parameters: `/user/{name}`
- Path converters: `/files/{path:path}` (captures full path including slashes)
- Automatic parameter extraction and validation

### Key Components to Implement
1. **Prompt loader module:** Scan directory, parse frontmatter, return prompt metadata
2. **Route matcher:** Dynamic FastAPI route registration based on prompt config
3. **Variable substitution:** Process prompt body with path parameters
4. **AI execution wrapper:** Pass processed prompt to provider, return raw output

### Directory Structure
```
data/
  prompts/
    hi.md           # GET /hi (fallback)
    calc.md         # GET /calculator (explicit route)
    user.md         # GET /user/{name} (with variables)
```

## Open Questions (Unanswered)

These questions were not addressed and should be considered for future refinement:

1. **Streaming responses:** Should we support streaming for long-running AI tasks? (e.g., Server-Sent Events)
2. **Concurrent request handling:** How should we handle multiple concurrent requests to the same prompt?
3. **Prompt file format validation:** Should we support formats other than Markdown? (e.g., `.txt`, `.yaml`)
4. **Route wildcards and regex:** Should we support advanced patterns like `/*` or regex routes?
5. **AI provider retry logic:** Should we retry on transient failures?
6. **Prompt versioning:** How to handle breaking changes to prompt files?
7. **Metrics and monitoring:** Should we expose Prometheus metrics?
8. **Request/response logging:** Should we log full request/response for audit trail?