# Goal

Build a rest server that runs codex commands and output the results

# Notes

These notes are a chatgpt brainstorm around this concept:

Good, this is a nice clean use-case for codex exec.

You want:
	•	HTTP server in Python
	•	On each request: spawn Codex, get output, process ends
	•	No long-living child process

Use subprocess.run (one-shot) + FastAPI.

⸻

1. Minimal FastAPI server wrapping codex exec

```python
# server.py
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

WORKDIR = "/path/to/your/project"   # where Codex should read/write files
TIMEOUT_SECONDS = 60               # safety timeout

class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    stdout: str
    stderr: str
    returncode: int

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        # One-shot Codex call. This process exits when done.
        result = subprocess.run(
            ["codex", "exec", req.prompt],
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        return ChatResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    except subprocess.TimeoutExpired as e:
        # If Codex hangs, kill it and return an error
        return ChatResponse(
            stdout=e.stdout or "",
            stderr=(e.stderr or "") + "\n[ERROR] Codex timed out",
            returncode=124,
        )
```

run it

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

call

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"create hello.txt with a short greeting"}'
```

	•	subprocess.run(...) blocks until Codex finishes, collects stdout/stderr, and the child process exits automatically.
	•	If it exceeds TIMEOUT_SECONDS, TimeoutExpired is raised and the subprocess is killed for you.

You don’t need to manually .kill() or .terminate() when using run like this.

⸻

2. If you do want manual kill control (Popen pattern)

Only if you ever go interactive / streaming:

```python
process = subprocess.Popen(
    ["codex", "exec", prompt],
    cwd=WORKDIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
# process is done here

# on timeout:
process.kill()
stdout, stderr = process.communicate()
```

But for your “one request → one Codex run → done” use case, the first subprocess.run version is exactly what you want.

# Personal considerations

- We should build a venv and freeze any dependencies so to be able to replicate the project.
- this is a first step so i'd like just a get://hello api that should ask codex to produce a random greeting
- focus on the interface between the server and the codex engine
- think also if it is possible to make such interface generic so to replace it with claude code of github copilot cli in the future

---

# Refined Implementation Plan

## Phase 1: Basic HTTP Server (Hello World) ✅
**Goal:** Verify server setup and infrastructure works

- [x] Create Python virtual environment (venv)
- [x] Install FastAPI and uvicorn
- [x] Create basic server with `GET /hello` endpoint returning "Hello, World!"
- [x] Test server runs correctly
- [x] Freeze dependencies to `requirements.txt`

**Completed:** December 1, 2025
**Files created:**
- `src/main.py` - FastAPI server with `/hello` and `/` endpoints
- `src/__init__.py` - Package initialization
- `requirements.txt` - Frozen dependencies
- `README.md` - Setup and usage documentation
- `.gitignore` - Python-specific ignore rules

## Testing Strategy

To enable autonomous testing during development:

### Test Implementation ✅

**Two-tier testing strategy:**

1. **Unit/Integration Tests** (`tests/test_main.py`)
   - Uses FastAPI `TestClient` (in-process, no HTTP server)
   - Fast, isolated testing of application logic
   - Good for rapid development

2. **E2E Tests** (`tests/test_e2e.py`)
   - Starts real uvicorn server on different ports
   - Makes actual HTTP requests over network
   - Tests full deployment stack including server startup, port binding, and error handling
   - Uses `ServerManager` context manager for lifecycle management

**Usage:**
```bash
# Run unit tests (fast)
pytest tests/test_main.py -v

# Run E2E tests (real server)
pytest tests/test_e2e.py -v

# Run all tests
pytest tests/ -v
```

The E2E tests enable autonomous error detection by running against a real server, capturing stdout/stderr, and testing actual network behavior.

### Test Structure
```
tests/
├── __init__.py
├── e2e_utils.py              # Server lifecycle management
├── test_main.py              # Unit tests (TestClient)
├── test_e2e.py               # E2E tests (real server)
├── test_providers.py         # AI provider tests (Phase 2)
└── test_integration.py       # Full integration tests (Phase 2)
```

## Phase 2: CLI Wrapper with Generic Interface ✅
**Goal:** Implement AI provider abstraction and Codex integration

**Completed:** December 1, 2025
**Files created:**
- `src/config.py` - Configuration management with environment variables
- `src/providers/base.py` - Abstract AIProvider base class and AIProviderResult
- `src/providers/codex.py` - CodexProvider implementation
- `src/providers/factory.py` - ProviderFactory for creating providers
- `tests/test_providers.py` - Comprehensive provider tests
- Updated `src/main.py` - Enhanced endpoints with AI provider integration
- Updated tests with mocking for all error scenarios

### Architecture Design:
```
AIProvider (ABC)
├── CodexProvider (default) ✅
├── ClaudeProvider (future)
└── CopilotProvider (future)
```

- [x] Create abstract `AIProvider` base class with `execute(prompt: str) -> AIProviderResult` method
- [x] Implement `CodexProvider` that wraps `codex exec` command
- [x] Add configuration system (env var or config file) to select provider
- [x] Update `/hello` endpoint to use AIProvider to generate greeting
- [x] Implement comprehensive error handling with appropriate HTTP status codes

### Configuration:
- **AI_PROVIDER**: Which provider to use (default: "codex")
- **WORKSPACE_DIR**: Where AI can create/modify files (default: "./data")
- **TIMEOUT_SECONDS**: Command timeout (default: 60)

### Error Handling Strategy:
- 200: Success with result
- 408: Request Timeout (AI command exceeded timeout)
- 500: Internal Server Error (AI command failed)
- 503: Service Unavailable (AI provider not configured/installed)
- Return JSON with error details: `{"error": "...", "details": "...", "provider": "..."}`

### Technical Specs:
- Python: 3.11
- Dependencies: FastAPI, uvicorn, pydantic
- Response format: Plain text for `/hello`
- Workspace: Configurable, default `./data/`

## File Structure:
```
codex-api/
├── venv/
├── data/                    # Default workspace for AI
├── src/
│   ├── __init__.py
│   ├── main.py             # FastAPI server
│   ├── config.py           # Configuration management
│   └── providers/
│       ├── __init__.py
│       ├── base.py         # AIProvider ABC
│       └── codex.py        # CodexProvider implementation
├── requirements.txt
└── README.md
```

