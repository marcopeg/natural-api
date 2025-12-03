# Testing Requirement

**Always run the tests after any code change.**
This ensures all features and error paths are validated automatically. Use:
```
pytest tests/ -v
```
or run specific suites as described above. Never skip this step.

# Goal
Build a REST wrapper around codex, claude-code or github copilot CLI tools with dynamic prompt-based routing.

# Architecture

## Project Structure

```
codex-api/
├── src/
│   ├── main.py              # FastAPI application with dynamic routing
│   ├── config.py            # Configuration management (env vars)
│   ├── prompts/
│   │   ├── loader.py        # Prompt file loading & parsing
│   │   ├── router.py        # Dynamic route matching
│   │   ├── variables.py     # Variable substitution
│   │   └── executor.py      # Prompt execution with AI
│   └── providers/
│       ├── base.py          # AIProvider abstract base class
│       ├── codex.py         # CodexProvider implementation
│       └── factory.py       # ProviderFactory (creates providers)
├── tests/
│   ├── test_main.py         # API endpoint tests
│   ├── test_e2e.py          # E2E tests with real HTTP server
│   ├── test_prompt_loader.py  # Prompt loading tests
│   ├── test_variables.py    # Variable substitution tests
│   ├── test_router.py       # Route matching tests
│   ├── test_executor.py     # Prompt execution tests
│   ├── test_providers.py    # Provider-specific tests
│   ├── e2e_utils.py         # ServerManager for E2E testing
│   └── fixtures/prompts/    # Test prompt files
├── data/
│   ├── prompts/             # User prompt files (*.md with YAML frontmatter)
│   └── *.txt                # AI workspace files
└── requirements.txt         # Python dependencies
```

## Technical Decisions

### 1. Dynamic Prompt-Based Routing (Phase 3)

**Overview:**
The API dynamically routes HTTP requests to AI prompts based on markdown files in `data/prompts/`. This allows adding new API endpoints without code changes - just create a new prompt file.

**Prompt File Location:**
- All prompts stored in: `data/prompts/*.md`
- Each `.md` file becomes an endpoint
- Subdirectories are NOT supported (prompts must be in root of `data/prompts/`)

**Prompt File Format:**
- YAML frontmatter (optional) defines metadata
- Body contains the actual prompt sent to AI
- Variables use bash-style syntax: `${variable}` or `${variable:default}`

**Naming Convention:**
- Filename (without `.md`) becomes the route if no explicit route specified
- Examples:
  - `hi.md` → accessible at `/hi`
  - `calc.md` → accessible at `/calc`
  - `user-profile.md` → accessible at `/user-profile`

**YAML Frontmatter Options:**
```yaml
---
route: /explicit/path/{param}    # Optional: Override default filename-based route
method: GET                        # Optional: Default is GET
model: gpt-5.1-codex-mini       # Optional: Override default model
agent: true                      # Optional: Use agent mode
---
```

**Route Matching (Two-Tier System):**
1. **Explicit routes first**: If frontmatter has `route:`, it's matched first
   - Supports path parameters: `/greet/{name}`, `/users/{id}`
   - Path parameters become variables in the prompt
2. **Fallback to filename**: If no explicit route matches, use filename
   - `hi.md` matches `/hi`
   - Only works for simple paths (no slashes)

**First match wins**: Files are checked in filesystem order, so be careful with overlapping routes

**Variable Substitution:**
- Bash-style syntax: `${variable}` or `${variable:default}`
- Variables come from:
  - Path parameters (e.g., `{name}` in route becomes `${name}` in prompt)
  - Query parameters (future enhancement)
- Missing variable with default: uses default value
- Missing variable without default: empty string

**Complete Example:**

File: `data/prompts/greet.md`
```markdown
---
route: /greet/{name}
method: GET
model: gpt-5.1-codex-mini
---

Generate a friendly greeting for ${name} with role ${role:guest}.
Include a fun fact about their role.
```

Usage:
- `GET /greet/Alice` → `${name}` = "Alice", `${role}` = "guest"
- `GET /greet/Bob` → `${name}` = "Bob", `${role}` = "guest"

**Simple Example (Filename-Based):**

File: `data/prompts/hi.md`
```markdown
---
method: GET
---

Generate a casual, friendly greeting. Make it upbeat and include a subtle joke.
```

Usage:
- `GET /hi` → Executes prompt and returns AI response

### 2. Provider Architecture

### 2. Provider Architecture

**Abstract Base Class Pattern:**
- `AIProvider` (ABC) defines interface: `execute(prompt, model=None) -> AIProviderResult`
- Each CLI tool gets its own provider class (e.g., `CodexProvider`)
- `ProviderFactory` creates providers based on configuration
- Easy to add new providers without modifying existing code

**Configuration-Driven:**
- Environment variable `AI_PROVIDER` selects which provider to use (default: "codex")
- `WORKSPACE_DIR` sets where AI can create/modify files (default: "./data")
- `PROMPTS_DIR` automatically set to `WORKSPACE_DIR/prompts`
- `TIMEOUT_SECONDS` controls command timeout (default: 60)
- `LOG_LEVEL` controls logging verbosity (default: "INFO")

**Why this approach:**
- Clean separation of concerns
- Easy to test with mocks
- Future-proof: add Claude/Copilot by implementing AIProvider interface
- Per-prompt provider/model overrides supported

### 3. Error Handling Strategy

**Comprehensive HTTP Status Codes:**
- `200` - Success
- `404` - Not Found (no matching prompt)
- `408` - Request Timeout (command exceeded timeout)
- `500` - Internal Server Error (command failed)
- `503` - Service Unavailable (provider not installed/configured)

**Structured Error Responses:**
```json
{
  "detail": {
    "error": "Error type",
    "message": "Detailed error message",
    "provider": "codex",
    "stderr": "command output"
  }
}
```

**Why this approach:**
- Clear, actionable error messages
- Proper HTTP semantics
- Includes diagnostic information (stderr, returncode)
- Client can programmatically handle different error types

### 4. Testing Strategy

**Three-Tier Testing:**

1. **Unit Tests** (`test_prompt_loader.py`, `test_variables.py`, `test_router.py`, `test_executor.py`, `test_providers.py`)
   - Test individual modules in isolation
   - Mock external dependencies
   - Fast, deterministic, comprehensive coverage
   - Test all edge cases and error scenarios

2. **Integration Tests** (`test_main.py`)
   - Use FastAPI's `TestClient` (in-process, no HTTP server)
   - Mock provider execution
   - Test API endpoint behavior
   - Validate request/response handling

3. **E2E Tests** (`test_e2e.py`)
   - Start real uvicorn server via `ServerManager` class
   - Make actual HTTP requests over network
   - Each test uses different port to avoid conflicts
   - Validates full deployment stack
   - **Important:** Mocking doesn't work in E2E tests (separate process)

**Why this approach:**
- Unit tests provide fast feedback during development
- Integration tests validate API layer
- E2E tests catch integration issues
- All tests can be run autonomously by CI/CD or AI agents
- E2E ServerManager handles cleanup automatically

### 5. Environment Setup

**Python 3.11 with Virtual Environment:**
```bash
# Create venv
python3.11 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Why Python 3.11:**
- Modern type hints (e.g., `str | None` instead of `Optional[str]`)
- Good balance of stability and features
- Well supported by FastAPI ecosystem

### 5. Running the Application

**Development mode (auto-reload):**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Production mode:**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**With custom configuration:**
```bash
export AI_PROVIDER=codex
export WORKSPACE_DIR=/custom/path
export TIMEOUT_SECONDS=120
export LOG_LEVEL=DEBUG
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Using Makefile:**
```bash
make start    # Start server in background
make kill     # Kill background server
make logs     # View server logs
```

**Important:** Always check for background processes before starting:
```bash
ps aux | grep uvicorn | grep -v grep
# If found, kill them: kill <PID>
```

**API Endpoints:**
- `GET /` - API information and instructions
- `GET /{path}` - Dynamic prompt-based routing (matches any path)
- Example: `GET /hi` matches `data/prompts/hi.md`
- Example: `GET /greet/Alice` matches `data/prompts/greet.md` with `name=Alice`

### 6. Testing Workflow

**Run all tests:**
```bash
pytest tests/ -v
```

**Run specific test suites:**
```bash
# Unit tests only (fast)
pytest tests/test_prompt_loader.py tests/test_variables.py tests/test_router.py tests/test_executor.py tests/test_providers.py -v

# Integration tests (API layer)
pytest tests/test_main.py -v

# E2E tests only (slower, real server)
pytest tests/test_e2e.py -v
```

**Test coverage:**
- Prompt loading with valid/invalid YAML
- Variable substitution with all edge cases
- Route matching (explicit and fallback)
- Prompt execution with model/agent overrides
- Provider factory behavior
- All error paths (timeout, failure, unavailable, not found)
- HTTP status codes

### 7. Key Design Patterns

**Factory Pattern:**
- `ProviderFactory.create()` centralizes provider instantiation
- Easy to register new providers
- Configuration validation in one place

**Result Object Pattern:**
- `AIProviderResult` encapsulates execution results
- Consistent interface for success/failure
- Includes all diagnostic info (stdout, stderr, returncode)

**Context Manager for Testing:**
- `running_server()` context manager in E2E tests
- Automatic cleanup even on test failure
- Clean API: `with running_server(port=8001) as server:`

**Dataclass Pattern:**
- `PromptMetadata` for structured prompt configuration
- `RouteMatch` for route matching results
- Type safety with minimal boilerplate

### 8. Future Considerations

**When adding new providers:**
1. Implement `AIProvider` abstract class
2. Add to `ProviderFactory._providers` registry
3. Add provider-specific tests
4. Update configuration documentation

**When adding new prompt files:**
1. Create `*.md` file in `data/prompts/`
2. Add YAML frontmatter with `route`, `method`, `model`, `agent` (all optional)
3. Use `${variable:default}` syntax for dynamic content
4. Test with curl or browser

**How to create a new endpoint (step-by-step):**

1. **Choose a name**: Use lowercase with hyphens (e.g., `user-profile`, `calc`, `hi`)

2. **Create the file**: `data/prompts/<name>.md`

3. **Add frontmatter (optional)**:
   ```yaml
   ---
   route: /custom/path/{param}  # Optional: override filename-based route
   method: GET                     # Optional: default is GET
   model: gpt-5.1-codex-mini    # Optional: override default model
   agent: true                   # Optional: use agent mode for complex tasks
   ---
   ```

4. **Write the prompt**: After the frontmatter, write the prompt that will be sent to the AI
   - Use `${variable}` for dynamic values from URL path parameters
   - Use `${variable:default}` to provide fallback values
   - Be specific about what you want the AI to generate

5. **Test it**:
   ```bash
   # If using filename-based route (no explicit route in frontmatter)
   curl http://localhost:8000/<name>
   
   # If using explicit route with parameters
   curl http://localhost:8000/custom/path/value
   ```

6. **No code changes needed**: The API automatically picks up new prompts

**Examples of existing prompts:**
- `hi.md` - Simple greeting (filename-based route)
- `calc.md` - Calculator (filename-based route)
- `greet.md` - Personalized greeting with path parameter (explicit route: `/greet/{name}`)

**Important reminders:**
- Prompt files must be in `data/prompts/` (no subdirectories)
- Filename becomes route if no explicit route specified
- First matching route wins (explicit routes checked before filename fallback)
- Variable substitution happens before sending to AI
- AI response is returned as plain text in HTTP response

**Deployment:**
- Current setup supports containerization (Docker)
- Environment variables make it 12-factor compliant
- Can run multiple instances on different ports
- Workspace directory should be mounted volume in production

# CLI References

## Codex CLI

### Available Models

Codex supports the following models (access via `-m` or `--model` flag):

1. **gpt-5.1-codex-max** (current) - Latest Codex-optimized flagship for deep and fast reasoning.
2. **gpt-5.1-codex** - Optimized for codex.
3. **gpt-5.1-codex-mini** - Optimized for codex. Cheaper, faster, but less capable.
4. **gpt-5.1** - Broad world knowledge with strong general reasoning.

Access legacy models by running `codex -m <model_name>` or in your `config.toml`.

### CLI Help

```bash
(venv) marpeg@mac-se-marpeg codex-api % codex --help
Codex CLI

If no subcommand is specified, options will be forwarded to the interactive CLI.

Usage: codex [OPTIONS] [PROMPT]
       codex [OPTIONS] <COMMAND> [ARGS]

Commands:
  exec        Run Codex non-interactively [aliases: e]
  login       Manage login
  logout      Remove stored authentication credentials
  mcp         [experimental] Run Codex as an MCP server and manage MCP servers
  mcp-server  [experimental] Run the Codex MCP server (stdio transport)
  app-server  [experimental] Run the app server or related tooling
  completion  Generate shell completion scripts
  sandbox     Run commands within a Codex-provided sandbox [aliases: debug]
  apply       Apply the latest diff produced by Codex agent as a `git apply` to your local working tree [aliases: a]
  resume      Resume a previous interactive session (picker by default; use --last to continue the most recent)
  cloud       [EXPERIMENTAL] Browse tasks from Codex Cloud and apply changes locally
  features    Inspect feature flags
  help        Print this message or the help of the given subcommand(s)

Arguments:
  [PROMPT]
          Optional user prompt to start the session

Options:
  -c, --config <key=value>
          Override a configuration value that would otherwise be loaded from `~/.codex/config.toml`. Use a dotted path (`foo.bar.baz`) to override nested values. The `value` portion is parsed as TOML. If it
          fails to parse as TOML, the raw string is used as a literal.
          
          Examples: - `-c model="o3"` - `-c 'sandbox_permissions=["disk-full-read-access"]'` - `-c shell_environment_policy.inherit=all`

      --enable <FEATURE>
          Enable a feature (repeatable). Equivalent to `-c features.<name>=true`

      --disable <FEATURE>
          Disable a feature (repeatable). Equivalent to `-c features.<name>=false`

  -i, --image <FILE>...
          Optional image(s) to attach to the initial prompt

  -m, --model <MODEL>
          Model the agent should use

      --oss
          Convenience flag to select the local open source model provider. Equivalent to -c model_provider=oss; verifies a local LM Studio or Ollama server is running

      --local-provider <OSS_PROVIDER>
          Specify which local provider to use (lmstudio or ollama). If not specified with --oss, will use config default or show selection

  -p, --profile <CONFIG_PROFILE>
          Configuration profile from config.toml to specify default options

  -s, --sandbox <SANDBOX_MODE>
          Select the sandbox policy to use when executing model-generated shell commands
          
          [possible values: read-only, workspace-write, danger-full-access]

  -a, --ask-for-approval <APPROVAL_POLICY>
          Configure when the model requires human approval before executing a command

          Possible values:
          - untrusted:  Only run "trusted" commands (e.g. ls, cat, sed) without asking for user approval. Will escalate to the user if the model proposes a command that is not in the "trusted" set
          - on-failure: Run all commands without asking for user approval. Only asks for approval if a command fails to execute, in which case it will escalate to the user to ask for un-sandboxed execution
          - on-request: The model decides when to ask the user for approval
          - never:      Never ask for user approval Execution failures are immediately returned to the model

      --full-auto
          Convenience alias for low-friction sandboxed automatic execution (-a on-request, --sandbox workspace-write)

      --dangerously-bypass-approvals-and-sandbox
          Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY DANGEROUS. Intended solely for running in environments that are externally sandboxed

  -C, --cd <DIR>
          Tell the agent to use the specified directory as its working root

      --search
          Enable web search (off by default). When enabled, the native Responses `web_search` tool is available to the model (no per‑call approval)

      --add-dir <DIR>
          Additional directories that should be writable alongside the primary workspace

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## Claude-Code CLI

```bash
to be completed
```

## GitHub Copilot CLI

```bash
to be completed
```
