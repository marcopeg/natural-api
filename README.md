# NaturalAPI

_NaturalAPI_ is a REST server (powered by [FastAPI](https://fastapi.tiangolo.com/)) that uses **Agentic CLI tools** 🤖 (Codex, ClaudeCode, GitHub Copilot) to implement server-side logic expressed in **Natural Language**.

# Overview

## Define REST endpoints in Markdown

An endpoint is defined as a _Markdown_ document, here is the source of `chuck-norris.md`:

```Markdown
Tell a Chuck Norris joke.
```

You can get the result of this "logic" at:

```bash
http://localhost:1337/chuck-norris
```

## OpenAPI Documentation

The API surface is build dynamically from the markdown documents you provide, and a OpenAPI compliant API documentation is provided at:

- **data:** http://localhost:1337/openapi.json
- **swagger:** http://localhost:1337/openapi

# Local Development

## Prerequisites
- Python 3.11
- Codex CLI (optional, for AI functionality)

## Installation

1. Clone the repository
```bash
git clone git@github.com:marcopeg/natural-api.git
cd natural-api
```

2. Create and activate virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the server:
```bash
# Manual
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Makefile
make start
```

5. Test it:
```bash
# Get API info
curl http://localhost:1337/

# Try a dynamic prompt (fallback route)
curl http://localhost:1337/hi

# Try a prompt with path parameters
curl http://localhost:1337/greet/Alice
```

## Dynamic Prompt-Based Routing

The server automatically maps HTTP requests to AI prompts stored in `data/projects/{project}/prompts/*.md`.

### Creating a Prompt

Create a Markdown file in your project's prompts directory (e.g., `data/projects/default/prompts/`):

**Example: `data/projects/default/prompts/greet.md`**
```markdown
---
route: /greet/{name}
verb: GET
model: gpt-5.1-codex-mini
---

Generate a warm, personalized greeting for ${name}. Make it friendly and creative.
```

### Frontmatter Options

```yaml
---
route: /path/{param}    # Optional: Explicit route (supports path parameters)
method: GET             # Optional: HTTP method (default: GET)
model: gpt-5.1-codex    # Optional: LLM model override
agent: codex            # Optional: AI provider override
dry: true               # Optional: Enable dry-run mode for this prompt
body:                   # Optional: Request body schema (POST/PUT/PATCH only)
  field_name:
    type: string        # Types: string, number, integer, boolean
    required: true      # Optional: default is false
    default: "value"    # Optional: default value
    minLength: 3        # Optional: string constraints
    maxLength: 100
    pattern: "^[A-Z]"   # Optional: regex pattern
    enum: [val1, val2]  # Optional: allowed values
    min: 0              # Optional: number constraints
    max: 100
    description: "..."  # Optional: field description
---
```

### Route Matching

The system uses two-tier matching:

1. **Explicit Routes** - Match prompts with `route` configuration
   - `route: /greet/{name}` matches `GET /greet/Alice`
   - Supports path parameters: `{name}`, `{id}`, etc.
   - Supports path wildcards: `{path:path}` (matches entire remaining path)

2. **Fallback Routes** - Match by filename
   - `hi.md` automatically creates `GET /hi`
   - Only matches GET requests
   - Single path segment only (no slashes)

### Variable Substitution

Use bash-style variables in prompt body:

**Syntax:**
- `${variable}` - Simple substitution (empty string if not found)
- `${variable:default}` - Substitution with default value
- `${route.variable}` - Explicit route parameter (from URL path)
- `${body.variable}` - Request body field (from POST/PUT/PATCH JSON)

**Variables come from:**
- Path parameters (e.g., `{name}` in route becomes `${name}` or `${route.name}`)
- Request body fields (e.g., JSON `{"text": "hello"}` becomes `${body.text}`)
- Future: Query parameters (`?role=admin` → `${query.role}`)

**Example with path parameters:**
```markdown
---
route: /user/{username}/profile
---

Create a profile for ${username} with occupation ${occupation:Software Developer}.
```

Request `GET /user/alice/profile` → Prompt: "Create a profile for alice with occupation Software Developer."

**Example with request body:**
```markdown
---
route: /analyze
method: POST
body:
  text:
    type: string
    required: true
  sentiment:
    type: string
    enum: [positive, negative, neutral]
    default: neutral
---

Analyze this text: "${body.text}"
Expected sentiment: ${body.sentiment}
```

Request:
```bash
curl -X POST http://localhost:1337/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "This is amazing!"}'
```

→ Prompt: "Analyze this text: \"This is amazing!\"\nExpected sentiment: neutral"

### Example Prompts

The project includes several example prompts in `data/projects/default/prompts/`:

- **`hi.md`** - Simple greeting (fallback route: `GET /hi`)
- **`calc.md`** - Calculator (explicit route: `GET /calculator`)
- **`greet.md`** - Personalized greeting (path param: `GET /greet/{name}`)
- **`analyze.md`** - Text analysis (POST with body validation)

Each project can have its own set of prompts. Create new projects by adding directories under `data/projects/`.

### API Endpoints

**Core Routes:**
- `GET /` - API information and available providers
- `GET /openapi.json?project={id}` - OpenAPI specification for project
- `GET /openapi?project={id}` - Swagger UI for interactive API testing

**Dynamic Routes (prompt-based):**
- Any path matching prompts in `data/projects/{project}/prompts/`
- Controlled by `X-Project-Id` header (default: `default`)
- Controlled by `X-User-Id` header (default: `anonymous`)
- Examples:
  - `GET /hi` - Random greeting (fallback route from `hi.md`)
  - `GET /calculator` - Sum calculation (explicit route from `calc.md`)
  - `GET /greet/Alice` - Personalized greeting with path parameter
  - `POST /analyze/hello` - Text sentiment analysis with request body

**Dry-Run Mode:**
- Add `?dry=true` query parameter or `X-Dry: true` header
- Returns command preview without execution
- CLI clients get markdown, browsers get HTML

### Configuration

Configure the server using environment variables:

```bash
# Select AI provider (default: codex)
export AI_PROVIDER=codex

# Set workspace directory (default: ./data)
export WORKSPACE_DIR=./data

# Set command timeout in seconds (default: 60)
export TIMEOUT_SECONDS=60

# Set logging level (default: INFO)
export LOG_LEVEL=DEBUG

# Enable OpenAPI endpoint (default: true)
export OPENAPI_ENABLED=true
```

### Multi-Project & Multi-User Support

**Project Isolation:**
```bash
# Use specific project
curl http://localhost:1337/hi -H "X-Project-Id: myproject"

# Projects stored in: data/projects/{project-id}/
```

**User Workspaces:**
```bash
# User-specific workspace
curl http://localhost:1337/hi -H "X-User-Id: alice" -H "X-Project-Id: myproject"

# Workspace: data/storage/{user-id}/{project-id}/
```

**Request Logging:**
- All requests logged to: `data/logs/{YYYY}/{MM}/{DD}/YYYYMMDD-HHMM-SSμμμμμμ-{status}.md`
- Includes: request details, AI command, execution output, response
- Format: Structured markdown with all context

### Testing

#### Automated Tests

The project includes comprehensive test coverage:

**1. Unit Tests (fast, mocked dependencies)**
```bash
# Test individual modules
pytest tests/test_prompt_loader.py -v    # Prompt loading & parsing
pytest tests/test_variables.py -v        # Variable substitution
pytest tests/test_router.py -v           # Route matching
pytest tests/test_executor.py -v         # Prompt execution
pytest tests/test_providers.py -v        # AI providers
pytest tests/test_main.py -v             # API endpoints
```

**2. E2E Tests (real server, actual HTTP requests)**
```bash
# Run E2E tests (starts real servers on different ports)
pytest tests/test_e2e.py -v
```

**Run all tests:**
```bash
source venv/bin/activate
pytest tests/ -v
```

**Quick test (skip slow E2E tests):**
```bash
pytest tests/ -v -k "not e2e_hello"
```

#### Manual Testing

With the server running:

```bash
# API info
curl http://localhost:1337/

# Dynamic prompts - fallback routes
curl http://localhost:1337/hi -H "X-Project-Id: default"

# Dynamic prompts - with path parameters
curl http://localhost:1337/greet/Alice -H "X-Project-Id: default"

# Dynamic prompts - POST requests with body
curl -X POST http://localhost:1337/analyze \
  -H "Content-Type: application/json" \
  -H "X-Project-Id: default" \
  -d '{"text": "This is amazing!"}'

# Dry-run mode (preview command)
curl "http://localhost:1337/hi?dry=true" -H "X-Project-Id: default"

# OpenAPI/Swagger UI
open http://localhost:1337/openapi?project=default

# Multi-project
curl http://localhost:1337/hi -H "X-Project-Id: test"

# Multi-user
curl http://localhost:1337/hi -H "X-User-Id: alice" -H "X-Project-Id: default"

# Check logs
ls -lh data/logs/$(date +%Y/%m/%d)/
```

## Development Workflow

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Start server with auto-reload
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 3. In another terminal, run tests
source venv/bin/activate
pytest tests/ -v
```

## Configuration

Configure the server using environment variables:

```bash
# Select AI provider (default: codex)
export AI_PROVIDER=codex

# Set workspace directory (default: ./data)
export WORKSPACE_DIR=./data

# Set command timeout in seconds (default: 60)
export TIMEOUT_SECONDS=60
```

## Architecture

### Provider System

```
AIProvider (Abstract Base Class)
├── CodexProvider (Codex CLI)
├── ClaudeProvider (Future)
└── CopilotProvider (Future)
```

**Current Providers:**
- `codex` - Wraps Codex CLI (`codex exec` commands)

**Configuration-driven:** Set `AI_PROVIDER` environment variable to switch providers.

### Prompt Routing System

```
HTTP Request
    ↓
DynamicRouter (load prompts from data/prompts/*.md)
    ↓
RouteMatch (explicit route or fallback filename)
    ↓
PromptExecutor (substitute variables, execute AI)
    ↓
AIProviderResult (return raw output)
```

**Key Components:**
- **PromptLoader** - Parses Markdown files with YAML frontmatter
- **DynamicRouter** - Matches requests to prompts (explicit then fallback)
- **VariableSubstitution** - Replaces `${var}` with path parameters
- **PromptExecutor** - Runs AI provider with processed prompt

### Error Handling

Comprehensive HTTP status codes:
- `200` - Success
- `404` - Not Found (no matching prompt)
- `408` - Request Timeout (AI command exceeded timeout)
- `500` - Internal Server Error (AI command failed)
- `503` - Service Unavailable (AI provider not configured/installed)

All errors return JSON with details:
```json
{
  "detail": {
    "error": "Error type",
    "message": "Detailed message",
    "provider": "codex"
  }
}
```

## Project Structure

```
natural-api/
├── src/
│   ├── main.py              # FastAPI application with dynamic routing
│   ├── config.py            # Configuration management (multi-project/user)
│   ├── prompts/
│   │   ├── loader.py        # Prompt file loading & parsing
│   │   ├── router.py        # Dynamic route matching
│   │   ├── variables.py     # Variable substitution
│   │   ├── executor.py      # Prompt execution with AI
│   │   └── body_validator.py # Request body schema validation
│   ├── providers/
│   │   ├── base.py          # AIProvider abstract base class
│   │   ├── codex.py         # CodexProvider implementation
│   │   └── factory.py       # ProviderFactory
│   ├── logging/
│   │   ├── models.py        # LogEntry dataclass
│   │   ├── timestamp.py     # Timestamp utilities
│   │   ├── formatter.py     # Markdown log formatter
│   │   ├── html_formatter.py # HTML formatter for browsers
│   │   ├── writer.py        # Log file writer
│   │   └── context.py       # Request logging context
│   └── openapi/
│       └── generator.py     # OpenAPI spec generation
├── tests/
│   ├── test_main.py         # API endpoint tests
│   ├── test_config.py       # Config tests (projects/users)
│   ├── test_prompt_loader.py # Prompt loading tests
│   ├── test_variables.py    # Variable substitution tests
│   ├── test_router.py       # Route matching tests
│   ├── test_executor.py     # Prompt execution tests
│   ├── test_providers.py    # Provider tests
│   ├── test_body_validator.py # Request body validation tests
│   ├── test_logging_*.py    # Logging system tests (27 tests)
│   ├── test_openapi_*.py    # OpenAPI tests
│   ├── test_e2e.py          # E2E tests (real server)
│   └── e2e_utils.py         # E2E utilities
├── data/
│   ├── projects/            # Multi-project support
│   │   ├── default/
│   │   │   ├── AGENTS.md    # Project-level AI instructions
│   │   │   └── prompts/     # Project-specific prompts
│   │   │       ├── hi.md
│   │   │       ├── calc.md
│   │   │       ├── greet.md
│   │   │       └── analyze.md
│   │   └── test/
│   │       └── prompts/
│   ├── storage/             # User workspaces per project
│   │   ├── anonymous/
│   │   │   └── default/     # User workspace
│   │   └── alice/
│   │       └── myproject/
│   └── logs/                # Request logs
│       └── {YYYY}/{MM}/{DD}/
│           └── YYYYMMDD-HHMM-SSμμμμμμ-{status}.md
└── requirements.txt         # Python dependencies
```

## License

MIT
