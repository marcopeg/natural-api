# Testing Requirement

Always activate the virtual environment and run tests after any code change.
This validates features and error paths automatically.

Recommended workflow (macOS/zsh):
```bash
# 1) Activate venv
source venv/bin/activate

# 2) Run full test suite
pytest tests/ -v

# 3) Optionally run focused suites
pytest tests/test_main.py -v
pytest tests/test_e2e.py -v
```
Never skip this step.

# Goal
Build a REST wrapper around Codex, Claude Code, or GitHub Copilot CLI tools with dynamic prompt-based routing.

# Architecture

## Project Structure

```
natural-api/
├── src/
│   ├── main.py              # FastAPI application with dynamic routing
│   ├── config.py            # Configuration (env vars, projects/users)
│   ├── prompts/
│   │   ├── loader.py        # Prompt file loading & parsing
│   │   ├── router.py        # Dynamic route matching
│   │   ├── variables.py     # Variable substitution (route/body)
│   │   ├── executor.py      # Prompt execution with AI
│   │   └── body_validator.py# Request body schema validation
│   ├── providers/
│   │   ├── base.py          # AIProvider abstract base class
│   │   ├── codex.py         # CodexProvider implementation
│   │   └── factory.py       # ProviderFactory (creates providers)
│   ├── logging/
│   │   ├── models.py        # LogEntry dataclass
│   │   ├── timestamp.py     # Timestamp utilities
│   │   ├── formatter.py     # Markdown log formatter
│   │   ├── html_formatter.py# HTML formatter for dry-run in browsers
│   │   └── writer.py        # Log file writer
│   └── openapi/
│       └── generator.py     # OpenAPI spec generation per project
├── tests/                   # Unit/Integration/E2E test suites
├── data/
│   ├── projects/            # Project information (agents and prompts)
│   │   └── <project-id>/
│   │       ├── AGENTS.md    # Project-level AI instructions
│   │       └── prompts/     # Project-specific prompts (*.md with YAML)
│   ├── storage/             # Per-user workspaces accessible at runtime
│   │   └── <user-id>/<project-id>/
│   └── logs/                # Request logs (YYYY/MM/DD/path)
└── requirements.txt         # Python dependencies
```

## Technical Decisions

### 1) Dynamic Prompt-Based Routing

Overview:
HTTP requests are routed to AI prompts defined as Markdown files in `data/projects/{project}/prompts/*.md`. Adding a new prompt file automatically adds a new API endpoint—no code changes required.

Prompt Location:
- Store prompts in: `data/projects/{project}/prompts/*.md`
- Subdirectories inside `prompts/` are not supported

Prompt Format:
- YAML frontmatter (optional) + body (prompt text)
- Variables use bash-style syntax: `${variable}` or `${variable:default}`

Frontmatter Options:
```yaml
---
route: /path/{param}         # Optional explicit route (supports params and wildcards)
method: GET                  # Optional HTTP method (default: GET)
model: gpt-5.1-codex-mini    # Optional model override
agent: codex                 # Optional provider override
dry: true                    # Optional default dry-run for this prompt
body:                        # Optional schema for request bodies (POST/PUT/PATCH)
        field_name:
                type: string             # Types: string, number, integer, boolean
                required: true           # Default: false
                default: value           # Optional default
                minLength: 3             # String constraints
                maxLength: 100
                pattern: "^[A-Z]"
                enum: [val1, val2]
                min: 0                   # Number constraints
                max: 100
                description: "..."
---
```

Route Matching (Two-Tier):
1. Explicit routes are matched first (frontmatter `route:`)
         - Supports path params: `/greet/{name}`, `/users/{id}`
         - Supports wildcards: `{path:path}` to match remaining path
2. Fallback routes by filename (GET only)
         - `hi.md` → `GET /hi` (single segment only)

First match wins. Be mindful of overlapping routes.

Variable Substitution:
- Syntax: `${name}`, `${name:default}`
- Sources:
        - Route params: `${name}` or `${route.name}`
        - Request body: `${body.field}` (POST/PUT/PATCH)
- Missing variable with default → default value; without default → empty string

Examples:
```markdown
---
route: /greet/{name}
method: GET
model: gpt-5.1-codex-mini
---
Generate a friendly greeting for ${name} with role ${role:guest}.
```

```markdown
---
route: /analyze
method: POST
body:
        text: { type: string, required: true }
        sentiment: { type: string, enum: [positive, negative, neutral], default: neutral }
---
Analyze this text: "${body.text}"
Expected sentiment: ${body.sentiment}
```

### 2) Provider Architecture

Abstract Base Class Pattern:
- `AIProvider` defines `execute(prompt, model=None) -> AIProviderResult`
- Providers: `codex` (current), future: `claude`, `copilot`
- `ProviderFactory` instantiates based on configuration

Configuration-Driven:
- `AI_PROVIDER` selects provider (default: `codex`)
- `WORKSPACE_DIR` root (default: `./data`)
- `TIMEOUT_SECONDS` (default: 60)
- `LOG_LEVEL` (default: `INFO`)

### 3) Error Handling

HTTP Status Codes:
- 200 Success
- 404 Not Found (no matching prompt)
- 408 Request Timeout (provider command exceeded timeout)
- 500 Internal Server Error (provider command failed)
- 503 Service Unavailable (provider missing/misconfigured)

Structured Error Responses:
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

### 4) Testing Strategy

Three-Tier Testing:
1. Unit Tests – modules in isolation, mocked dependencies
2. Integration Tests – FastAPI TestClient, API behavior
3. E2E Tests – real uvicorn server + real HTTP requests

Run Suites:
```bash
source venv/bin/activate

# All tests
pytest tests/ -v

# Unit suites
pytest tests/test_prompt_loader.py tests/test_variables.py tests/test_router.py tests/test_executor.py tests/test_providers.py -v

# Integration
pytest tests/test_main.py -v

# E2E
pytest tests/test_e2e.py -v
```

### 5) Environment Setup

Python 3.11 with Virtual Environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6) Running the Application

Development (auto-reload):
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Production:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Custom configuration:
```bash
export AI_PROVIDER=codex
export WORKSPACE_DIR=./data
export TIMEOUT_SECONDS=120
export LOG_LEVEL=DEBUG
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Makefile helpers:
```bash
make start
make kill
make logs
```

Before starting, ensure no background uvicorn processes are running:
```bash
ps aux | grep uvicorn | grep -v grep
```

### 7) API Endpoints

- `GET /` – API information and providers
- `GET /openapi.json?project={id}` – OpenAPI spec for project
- `GET /openapi?project={id}` – Swagger UI
- Dynamic routes resolve via project prompts and method matching

### 8) Multi-Project & Multi-User Support

Projects (information directory):
- Prompts per project in `data/projects/{project}/prompts/*.md`
- `AGENTS.md` holds project-level AI guidance

Storage (per-user runtime workspace):
- `data/storage/{user-id}/{project-id}/` holds user data accessible by agents

Headers:
- `X-Project-Id` selects project (default: `default`)
- `X-User-Id` selects user workspace (default: `anonymous`)

Request Logging:
- Logs at `data/logs/{YYYY}/{MM}/{DD}/YYYYMMDD-HHMM-SSμμμμμμ-{status}.md`
- Includes request, resolved prompt, provider command, output, and response

Dry-Run Mode:
- `?dry=true` or header `X-Dry: true`
- CLI clients receive markdown; browsers receive HTML preview

### 9) Future Considerations

- Query parameter substitution (`${query.role}`)
- Prompt caching + hot reload
- Debug endpoint (`/_debug/routes`)
- Response headers (`X-AI-Provider`, `X-Execution-Time`)
- Auth, rate limiting, isolation
- Streaming responses (SSE)
- Additional providers (Claude, Copilot)
- Log searching and a Web UI

# CLI References

## Codex CLI

Available Models (via `-m`/`--model`):
1. gpt-5.1-codex-max (current)
2. gpt-5.1-codex
3. gpt-5.1-codex-mini
4. gpt-5.1

CLI Help (excerpt):
```bash
codex --help
```

## Claude-Code CLI

```bash
to be completed
```

## GitHub Copilot CLI

```bash
to be completed
```
