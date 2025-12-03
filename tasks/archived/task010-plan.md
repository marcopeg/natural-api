# Task 010 Execution Plan: Request Logging System

## Overview
Implement comprehensive request logging for all API requests, capturing request metadata, AI execution details, and responses in structured markdown files organized by date. Support dry-run mode that returns log preview as HTML instead of writing to disk.

## Current State Analysis

### Existing Architecture
- **Request Handler**: `dynamic_prompt_handler` in `src/main.py` handles all dynamic routes
- **Provider Execution**: `CodexProvider.execute()` currently prints output to console with capture
- **Dry-Run Support**: Already implemented via `dry_run` parameter through prompt/header/query
- **Configuration**: `Config` class in `src/config.py` manages workspace paths
- **Error Handling**: Comprehensive HTTP exceptions with structured detail objects

### Key Touchpoints
1. **`src/main.py`**: Main request handler that needs logging integration
2. **`src/providers/codex.py`**: Provider that executes commands and captures output
3. **`src/prompts/executor.py`**: Executor that calls providers
4. **`src/config.py`**: Configuration for workspace and new log directory paths

### Current Flow
```
Request → dynamic_prompt_handler → PromptExecutor.execute → Provider.execute → Response
```

### Challenges Identified
1. **Output Capture**: Provider currently prints to console; need to capture while preserving streaming
2. **Command Reconstruction**: Need to access actual CLI command string (currently in provider)
3. **Error Context**: Must log even when exceptions occur (404, 500, timeout)
4. **Dry-Run Branching**: Must prevent log writes but still generate log preview
5. **Duration Tracking**: Need to measure from handler start to response generation
6. **Response Capture**: Need to capture final response before returning to client

---

## Phase 1: Foundation & Infrastructure

### Task 1.1: Logging Module Structure
**File**: `src/logging/__init__.py`
- Create new `src/logging/` directory
- Add `__init__.py` to make it a package

**File**: `src/logging/models.py`
- Create `LogEntry` dataclass to hold all log data:
  - `timestamp: datetime`
  - `status_code: int`
  - `method: str`
  - `path: str`
  - `project_id: str`
  - `user_id: str`
  - `prompt_filename: str | None`
  - `duration_ms: int`
  - `command: str`
  - `headers: dict[str, str]`
  - `ai_output: str`
  - `response_body: str`
  - `error_context: str | None`

**Dependencies**: None
**Estimated Complexity**: Low

### Task 1.2: Timestamp Utilities
**File**: `src/logging/timestamp.py`
- Implement `generate_timestamp()` → returns `datetime` (UTC now)
- Implement `format_filename_timestamp(dt)` → `"YYYYMMDD-HHMM-SSμμμμμμ"`
- Implement `format_title_timestamp(dt)` → `"YYYY/MM/DD HH:MM:SS.μμμμμμ UTC"`
- Implement `format_folder_path(dt)` → `"YYYY/MM/DD"`

**Example**:
```python
from datetime import datetime, timezone

def generate_timestamp() -> datetime:
    return datetime.now(timezone.utc)

def format_filename_timestamp(dt: datetime) -> str:
    return (
        dt.strftime("%Y%m%d-%H%M-") +
        dt.strftime("%S") +
        f"{dt.microsecond:06d}"
    )
```

**Dependencies**: None
**Estimated Complexity**: Low

### Task 1.3: Configuration Updates
**File**: `src/config.py`
- Add `LOGS_DIR: Path = WORKSPACE_DIR / "logs"` class variable
- Add `@classmethod get_logs_dir(cls) -> Path` method (creates if not exists)
- Add `@classmethod get_log_file_path(cls, timestamp: datetime, status_code: int) -> Path`
  - Constructs full path: `logs/YYYY/MM/DD/YYYYMMDD-HHMM-SSμμμμμμ-{code}.md`
  - Creates parent directories

**Example**:
```python
@classmethod
def get_log_file_path(cls, timestamp: datetime, status_code: int) -> Path:
    from src.logging.timestamp import format_filename_timestamp, format_folder_path
    
    folder_path = cls.LOGS_DIR / format_folder_path(timestamp)
    folder_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{format_filename_timestamp(timestamp)}-{status_code}.md"
    return folder_path / filename
```

**Dependencies**: Task 1.2
**Estimated Complexity**: Low

---

## Phase 2: Log Formatting & Generation

### Task 2.1: Markdown Log Formatter
**File**: `src/logging/formatter.py`
- Implement `format_log_markdown(entry: LogEntry) -> str`
- Generate complete markdown with all sections:
  - Title with formatted timestamp
  - Metadata table
  - Command section (bash code block)
  - Headers table (only X-Project-Id, X-User-Id, X-Dry)
  - AI Output section (text code block)
  - Response section (JSON or text preview)

**Example Structure**:
```python
def format_log_markdown(entry: LogEntry) -> str:
    from src.logging.timestamp import format_title_timestamp
    
    sections = [
        f"# {format_title_timestamp(entry.timestamp)}",
        "",
        _format_metadata_table(entry),
        "",
        _format_command_section(entry.command),
        "",
        _format_headers_table(entry.headers),
        "",
        _format_ai_output_section(entry.ai_output),
        "",
        _format_response_section(entry.response_body, entry.status_code),
    ]
    return "\n".join(sections)
```

**Special Cases**:
- If `prompt_filename` is None (404 error), show "not-found"
- If `ai_output` is empty, show "No execution"
- If `error_context`, append to Duration field: `"1000ms (timeout)"`
- Truncate response if > 10KB, add note "... (truncated)"

**Dependencies**: Task 1.1, Task 1.2
**Estimated Complexity**: Medium

### Task 2.2: HTML Formatter for Dry-Run
**File**: `src/logging/html_formatter.py`
- Implement `format_log_html(log_markdown: str) -> str`
- Wrap markdown in HTML template with styling
- Use simple pre-formatted display (no markdown rendering needed)

**Example**:
```python
def format_log_html(log_markdown: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Dry-Run Log Preview</title>
    <style>
        body {{ font-family: monospace; white-space: pre-wrap; padding: 20px; background: #f9f9f9; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; }}
        .command {{ background: #f4f4f4; padding: 10px; border-left: 3px solid #333; }}
    </style>
</head>
<body>{log_markdown}</body>
</html>"""
```

**Dependencies**: None
**Estimated Complexity**: Low

### Task 2.3: Log Writer
**File**: `src/logging/writer.py`
- Implement `write_log(entry: LogEntry) -> Path`
  - Generates markdown via formatter
  - Gets file path from config
  - Writes to disk (synchronous)
  - Returns path to written file
  - Raises `IOError` on failure

**Example**:
```python
def write_log(entry: LogEntry) -> Path:
    from src.logging.formatter import format_log_markdown
    from src.config import config
    
    log_path = config.get_log_file_path(entry.timestamp, entry.status_code)
    log_content = format_log_markdown(entry)
    
    try:
        log_path.write_text(log_content, encoding='utf-8')
        return log_path
    except Exception as e:
        raise IOError(f"Failed to write log file: {e}") from e
```

**Dependencies**: Task 1.3, Task 2.1
**Estimated Complexity**: Low

---

## Phase 3: Provider Output Capture

### Task 3.1: Modify AIProviderResult
**File**: `src/providers/base.py`
- Add `command: str` field to `AIProviderResult` dataclass
- Store the actual CLI command string that was executed (or would be in dry-run)
- Update `to_dict()` to include command

**Example**:
```python
class AIProviderResult:
    def __init__(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        success: bool,
        command: str,  # NEW
        error_message: str | None = None
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.success = success
        self.command = command  # NEW
        self.error_message = error_message
```

**Dependencies**: None
**Estimated Complexity**: Low

### Task 3.2: Update CodexProvider Command Capture
**File**: `src/providers/codex.py`
- Build command string using `shlex.quote()` for readability
- Store command in result for both normal and dry-run execution
- Ensure command is captured even on timeout/failure

**Changes**:
```python
# Build readable command string
import shlex
cmd_list = ["codex", "exec", "--sandbox", "workspace-write"]
if model:
    cmd_list.extend(["--model", model])
else:
    cmd_list.extend(["--model", "gpt-5.1-codex-mini"])
cmd_list.append(prompt)

command_string = " ".join(shlex.quote(arg) for arg in cmd_list)

# Store in all result returns
return AIProviderResult(
    stdout=...,
    stderr=...,
    returncode=...,
    success=...,
    command=command_string,  # NEW
    error_message=...
)
```

**Dependencies**: Task 3.1
**Estimated Complexity**: Low

### Task 3.3: Output Streaming Preservation
**Current State**: `CodexProvider` uses `capture_output=True`, then prints stdout/stderr after completion.

**Challenge**: Need real-time streaming to console while capturing for logs.

**Solution Options**:
1. **Keep current approach** (simplest): Output already captured, print after execution
   - Pros: No code change needed, synchronous, simple
   - Cons: Not true real-time (user sees output after completion)
2. **Subprocess streaming**: Use `Popen` with line-by-line reading
   - Pros: True real-time streaming
   - Cons: More complex, need to handle threading/buffering

**Decision**: Keep current approach (Option 1) for initial implementation
- User sees full output quickly after execution completes
- Still feels "real-time" for short-running commands
- Simpler error handling
- Can enhance later if needed

**No code changes needed for this task**

**Dependencies**: None
**Estimated Complexity**: None (design decision)

---

## Phase 4: Main Integration

### Task 4.1: Request Context Wrapper
**File**: `src/logging/context.py`
- Create `RequestLogContext` class to manage logging state throughout request lifecycle
- Tracks all data needed for final log entry
- Provides methods to update context as request progresses

**Example**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from src.logging.timestamp import generate_timestamp
from src.logging.models import LogEntry

class RequestLogContext:
    def __init__(self, method: str, path: str, project_id: str, user_id: str, headers: dict):
        self.timestamp = generate_timestamp()
        self.start_time = time.time()
        self.method = method
        self.path = path
        self.project_id = project_id
        self.user_id = user_id
        self.headers = headers
        
        # Updated during request processing
        self.prompt_filename: str | None = None
        self.command: str = "none"
        self.ai_output: str = ""
        self.response_body: str = ""
        self.status_code: int = 500  # Default to error
        self.error_context: str | None = None
    
    def set_prompt(self, filename: str):
        self.prompt_filename = filename
    
    def set_execution_result(self, result: AIProviderResult):
        self.command = result.command
        self.ai_output = f"{result.stdout}\n{result.stderr}".strip()
    
    def set_response(self, body: str, status: int):
        self.response_body = body
        self.status_code = status
    
    def set_error(self, context: str):
        self.error_context = context
    
    def get_duration_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)
    
    def to_log_entry(self) -> LogEntry:
        # Filter headers to only X-Project-Id, X-User-Id, X-Dry
        filtered_headers = {
            k: v for k, v in self.headers.items()
            if k.lower() in ['x-project-id', 'x-user-id', 'x-dry']
        }
        
        return LogEntry(
            timestamp=self.timestamp,
            status_code=self.status_code,
            method=self.method,
            path=self.path,
            project_id=self.project_id,
            user_id=self.user_id,
            prompt_filename=self.prompt_filename,
            duration_ms=self.get_duration_ms(),
            command=self.command,
            headers=filtered_headers,
            ai_output=self.ai_output,
            response_body=self.response_body,
            error_context=self.error_context
        )
```

**Dependencies**: Task 1.1, Task 1.2, Task 3.1
**Estimated Complexity**: Medium

### Task 4.2: Integrate Logging into Handler
**File**: `src/main.py`
- Wrap entire `dynamic_prompt_handler` with logging context
- Create `RequestLogContext` at start of handler
- Update context as request progresses
- Write log before returning response (normal mode)
- Return HTML log preview in dry-run mode
- Ensure logging happens even on exceptions (try/finally or exception handlers)

**Integration Points**:
```python
async def dynamic_prompt_handler(request: Request, path: str):
    from src.logging.context import RequestLogContext
    from src.logging.writer import write_log
    from src.logging.formatter import format_log_markdown
    from src.logging.html_formatter import format_log_html
    
    # 1. Initialize context at start
    log_ctx = RequestLogContext(
        method=request.method,
        path=f"/{path}" if path else "/",
        project_id="default",  # Will be updated
        user_id="anonymous",   # Will be updated
        headers=dict(request.headers)
    )
    
    try:
        # Existing code...
        project_id = extract_header(...)
        user_id = extract_header(...)
        
        # Update context with resolved IDs
        log_ctx.project_id = project_id
        log_ctx.user_id = user_id
        
        # Match route
        match = router.match_route(method, full_path)
        if not match:
            log_ctx.set_response(
                json.dumps({"error": "Not Found", ...}),
                404
            )
            raise HTTPException(status_code=404, ...)
        
        # Update context with prompt
        log_ctx.set_prompt(match.prompt.filename)
        
        # Determine dry-run
        dry_run = ...
        
        # DRY-RUN MODE: Return HTML preview instead of executing
        if dry_run:
            # Build mock log entry
            log_ctx.command = _build_mock_command(match.prompt, provider_name)
            log_ctx.ai_output = "Not executed (dry-run mode)"
            log_ctx.response_body = "Dry-run - no AI execution"
            log_ctx.status_code = 200
            
            # Generate HTML
            log_entry = log_ctx.to_log_entry()
            log_markdown = format_log_markdown(log_entry)
            html = format_log_html(log_markdown)
            
            return HTMLResponse(content=html, status_code=200)
        
        # NORMAL MODE: Execute and log
        result = executor.execute(...)
        
        # Update context with execution result
        log_ctx.set_execution_result(result)
        
        if result.returncode == 124:
            log_ctx.set_error("timeout")
            log_ctx.set_response(
                json.dumps({"error": "Request Timeout", ...}),
                408
            )
            raise HTTPException(status_code=408, ...)
        
        if not result.success:
            log_ctx.set_error("execution_failed")
            log_ctx.set_response(
                json.dumps({"error": "Internal Server Error", ...}),
                500
            )
            raise HTTPException(status_code=500, ...)
        
        # Success
        log_ctx.set_response(result.stdout, 200)
        
        # Write log
        try:
            log_path = write_log(log_ctx.to_log_entry())
            logger.debug(f"Request logged to: {log_path}")
        except IOError as e:
            logger.error(f"Failed to write log: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Logging Failed",
                    "message": f"Failed to write request log: {str(e)}"
                }
            )
        
        return PlainTextResponse(content=result.stdout)
        
    except HTTPException as e:
        # Update context with error response
        log_ctx.set_response(
            json.dumps(e.detail) if isinstance(e.detail, dict) else str(e.detail),
            e.status_code
        )
        
        # Write log even for errors (unless dry-run)
        if not dry_run:
            try:
                write_log(log_ctx.to_log_entry())
            except IOError as log_err:
                logger.error(f"Failed to write error log: {log_err}")
        
        raise  # Re-raise HTTP exception
    
    except Exception as e:
        # Unexpected errors
        log_ctx.set_error("unexpected_error")
        log_ctx.set_response(
            json.dumps({"error": "Internal Server Error", "message": str(e)}),
            500
        )
        
        # Try to log
        try:
            write_log(log_ctx.to_log_entry())
        except:
            pass  # Don't fail on log write during unexpected error
        
        raise HTTPException(status_code=500, detail={"error": "Internal Server Error", ...})
```

**Challenges**:
- Need to track dry-run flag to prevent logging in dry-run mode
- Must log even when exceptions occur
- Need to build mock command for dry-run preview
- Header filtering (only X-Project-Id, X-User-Id, X-Dry)

**Dependencies**: Task 2.1, Task 2.2, Task 2.3, Task 4.1
**Estimated Complexity**: High

### Task 4.3: Mock Command Builder for Dry-Run
**File**: `src/main.py` (helper function)
- Create `_build_mock_command()` to construct command string for dry-run preview
- Use same logic as provider but without execution
- Ensure command is formatted for maximum readability

**Example**:
```python
def _build_mock_command(prompt: PromptMetadata, provider_name: str) -> str:
    """Build readable command string for dry-run mode"""
    import shlex
    
    if provider_name == "codex":
        cmd_parts = ["codex", "exec", "--sandbox", "workspace-write"]
        if prompt.model:
            cmd_parts.extend(["--model", prompt.model])
        else:
            cmd_parts.extend(["--model", "gpt-5.1-codex-mini"])
        cmd_parts.append(prompt.raw_content[:100] + "...")  # Truncate for preview
        
        return " ".join(shlex.quote(arg) for arg in cmd_parts)
    
    return "unknown-provider"
```

**Dependencies**: None
**Estimated Complexity**: Low

---

## Phase 5: Testing

### Task 5.1: Unit Tests for Timestamp Utilities
**File**: `tests/test_logging_timestamp.py`
- Test `generate_timestamp()` returns UTC datetime
- Test `format_filename_timestamp()` produces correct format
- Test `format_title_timestamp()` produces correct format
- Test `format_folder_path()` produces correct format
- Use fixed datetime for deterministic testing (mock `datetime.now`)

**Example**:
```python
from datetime import datetime, timezone
from unittest.mock import patch
from src.logging.timestamp import format_filename_timestamp

def test_format_filename_timestamp():
    dt = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    result = format_filename_timestamp(dt)
    assert result == "20251203-1415-30123456"

def test_filename_timestamp_maintains_sort_order():
    dt1 = datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc)
    dt2 = datetime(2025, 12, 3, 14, 15, 31, 456789, tzinfo=timezone.utc)
    dt3 = datetime(2025, 12, 3, 14, 16, 0, 0, tzinfo=timezone.utc)
    
    ts1 = format_filename_timestamp(dt1)
    ts2 = format_filename_timestamp(dt2)
    ts3 = format_filename_timestamp(dt3)
    
    assert ts1 < ts2 < ts3  # Lexicographic sort = chronological sort
```

**Dependencies**: Task 1.2
**Estimated Complexity**: Low

### Task 5.2: Unit Tests for Log Formatter
**File**: `tests/test_logging_formatter.py`
- Test `format_log_markdown()` produces correct structure
- Test all sections are present
- Test header filtering (only X-Project-Id, X-User-Id, X-Dry)
- Test command formatting
- Test response truncation for large responses
- Test error context in duration field
- Mock all dependencies, no file I/O

**Example**:
```python
from src.logging.models import LogEntry
from src.logging.formatter import format_log_markdown
from datetime import datetime, timezone

def test_format_log_markdown_structure():
    entry = LogEntry(
        timestamp=datetime(2025, 12, 3, 14, 15, 30, 123456, tzinfo=timezone.utc),
        status_code=200,
        method="GET",
        path="/hi",
        project_id="default",
        user_id="anonymous",
        prompt_filename="hi.md",
        duration_ms=1000,
        command="codex exec 'prompt'",
        headers={"X-Project-Id": "default", "X-User-Id": "anonymous"},
        ai_output="Hello!",
        response_body="Hello!",
        error_context=None
    )
    
    markdown = format_log_markdown(entry)
    
    assert "# 2025/12/03 14:15:30.123456 UTC" in markdown
    assert "| Status    | 200" in markdown
    assert "| Duration  | 1000ms" in markdown
    assert "```bash" in markdown
    assert "codex exec 'prompt'" in markdown
    assert "## AI Output" in markdown

def test_format_log_markdown_with_error_context():
    entry = LogEntry(
        # ... same as above ...
        duration_ms=1000,
        error_context="timeout"
    )
    
    markdown = format_log_markdown(entry)
    assert "| Duration  | 1000ms (timeout)" in markdown
```

**Dependencies**: Task 2.1
**Estimated Complexity**: Medium

### Task 5.3: Unit Tests for HTML Formatter
**File**: `tests/test_logging_html_formatter.py`
- Test `format_log_html()` wraps markdown in HTML
- Test HTML structure (DOCTYPE, head, body, style)
- Test escaping (ensure no XSS if markdown contains HTML)

**Example**:
```python
from src.logging.html_formatter import format_log_html

def test_format_log_html_structure():
    markdown = "# Test Log\n\nSome content"
    html = format_log_html(markdown)
    
    assert "<!DOCTYPE html>" in html
    assert "<html>" in html
    assert "<head>" in html
    assert "<title>Dry-Run Log Preview</title>" in html
    assert "<style>" in html
    assert markdown in html
```

**Dependencies**: Task 2.2
**Estimated Complexity**: Low

### Task 5.4: Unit Tests for Log Writer
**File**: `tests/test_logging_writer.py`
- Test `write_log()` calls formatter and writes to correct path
- Mock file system operations (no actual writes)
- Test IOError is raised on write failure
- Mock `config.get_log_file_path()`

**Example**:
```python
from unittest.mock import patch, MagicMock
from src.logging.writer import write_log
from src.logging.models import LogEntry
from datetime import datetime, timezone

@patch('src.logging.writer.config.get_log_file_path')
@patch('pathlib.Path.write_text')
def test_write_log_success(mock_write, mock_get_path):
    mock_path = MagicMock()
    mock_get_path.return_value = mock_path
    
    entry = LogEntry(
        timestamp=datetime.now(timezone.utc),
        status_code=200,
        method="GET",
        path="/hi",
        project_id="default",
        user_id="anonymous",
        prompt_filename="hi.md",
        duration_ms=1000,
        command="codex exec 'hi'",
        headers={},
        ai_output="output",
        response_body="response",
        error_context=None
    )
    
    result = write_log(entry)
    
    assert result == mock_path
    mock_write.assert_called_once()

@patch('src.logging.writer.config.get_log_file_path')
@patch('pathlib.Path.write_text', side_effect=OSError("Disk full"))
def test_write_log_failure(mock_write, mock_get_path):
    entry = LogEntry(...)  # Same as above
    
    with pytest.raises(IOError, match="Failed to write log file"):
        write_log(entry)
```

**Dependencies**: Task 2.3
**Estimated Complexity**: Low

### Task 5.5: Unit Tests for Request Context
**File**: `tests/test_logging_context.py`
- Test `RequestLogContext` initialization
- Test context update methods
- Test `to_log_entry()` conversion
- Test header filtering
- Test duration calculation
- Mock `time.time()` for deterministic duration

**Example**:
```python
from unittest.mock import patch
from src.logging.context import RequestLogContext

@patch('time.time', side_effect=[1000.0, 1001.5])  # Start, then 1.5s later
def test_request_context_duration(mock_time):
    ctx = RequestLogContext(
        method="GET",
        path="/hi",
        project_id="default",
        user_id="anonymous",
        headers={}
    )
    
    duration = ctx.get_duration_ms()
    assert duration == 1500  # 1.5 seconds = 1500ms

def test_request_context_header_filtering():
    ctx = RequestLogContext(
        method="GET",
        path="/hi",
        project_id="default",
        user_id="anonymous",
        headers={
            "X-Project-Id": "test",
            "X-User-Id": "alice",
            "X-Dry": "true",
            "Authorization": "Bearer secret",  # Should be filtered
            "User-Agent": "curl/7.79.1"        # Should be filtered
        }
    )
    
    entry = ctx.to_log_entry()
    
    assert "X-Project-Id" in entry.headers
    assert "X-User-Id" in entry.headers
    assert "X-Dry" in entry.headers
    assert "Authorization" not in entry.headers
    assert "User-Agent" not in entry.headers
```

**Dependencies**: Task 4.1
**Estimated Complexity**: Medium

### Task 5.6: Integration Test for Dry-Run HTML Response
**File**: `tests/test_main.py` (add to existing file)
- Test dry-run mode returns HTMLResponse
- Test HTML contains log preview
- Test no log file is written
- Use FastAPI TestClient (in-process, no server needed)
- Mock `write_log` to ensure it's NOT called

**Example**:
```python
from fastapi.testclient import TestClient
from unittest.mock import patch

def test_dry_run_returns_html_preview():
    with patch('src.main.write_log') as mock_write:
        client = TestClient(app)
        response = client.get(
            "/hi?dry=true",
            headers={"x-project-id": "test", "x-user-id": "test"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "<!DOCTYPE html>" in response.text
        assert "Dry-Run Log Preview" in response.text
        assert "codex exec" in response.text  # Command preview
        
        # Ensure log was NOT written
        mock_write.assert_not_called()
```

**Dependencies**: Task 4.2
**Estimated Complexity**: Medium

---

## Phase 6: Validation & Polish

### Task 6.1: Manual Testing
- Start server locally
- Make various requests (success, 404, 500, timeout)
- Verify log files are created in correct locations
- Check file naming and sorting in Finder
- Verify log content completeness
- Test dry-run mode returns HTML
- Test header filtering
- Check console output still works

### Task 6.2: Error Scenarios Testing
- Test disk full scenario (mock in tests)
- Test permission denied (mock in tests)
- Test timeout with partial output
- Test 404 with no prompt match
- Test validation errors (400, 422)

### Task 6.3: Documentation Updates
**File**: `.github/copilot-instructions.md`
- Document new logging system
- Add section on log file structure
- Document dry-run preview feature
- Update testing guidelines

---

## Deliverables Checklist

### Code Deliverables
- [ ] `src/logging/__init__.py` - Package initialization
- [ ] `src/logging/models.py` - LogEntry dataclass
- [ ] `src/logging/timestamp.py` - Timestamp utilities
- [ ] `src/logging/formatter.py` - Markdown log formatter
- [ ] `src/logging/html_formatter.py` - HTML formatter for dry-run
- [ ] `src/logging/writer.py` - Log file writer
- [ ] `src/logging/context.py` - RequestLogContext class
- [ ] `src/config.py` - Updated with log directory methods
- [ ] `src/providers/base.py` - AIProviderResult with command field
- [ ] `src/providers/codex.py` - Command capture in results
- [ ] `src/main.py` - Integrated logging in handler

### Test Deliverables
- [ ] `tests/test_logging_timestamp.py` - Timestamp utilities tests
- [ ] `tests/test_logging_formatter.py` - Markdown formatter tests
- [ ] `tests/test_logging_html_formatter.py` - HTML formatter tests
- [ ] `tests/test_logging_writer.py` - Writer tests
- [ ] `tests/test_logging_context.py` - Context tests
- [ ] `tests/test_main.py` - Updated with dry-run HTML test
- [ ] All existing tests still pass

### Functional Deliverables
- [ ] All requests logged to `data/logs/YYYY/MM/DD/` with correct naming
- [ ] Log files contain all required sections
- [ ] Dry-run mode returns HTML preview instead of writing logs
- [ ] Console output still streams in real-time (or appears real-time)
- [ ] Error requests (404, 500, etc.) are logged
- [ ] Partial logs written for timeouts
- [ ] Log write failures result in 500 errors
- [ ] Headers filtered to only X-Project-Id, X-User-Id, X-Dry

### Quality Gates
- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] Test coverage > 80% for new logging modules
- [ ] No regression in existing functionality
- [ ] Code follows existing style conventions
- [ ] No new pylint/mypy errors
- [ ] Manual testing confirms all scenarios work

---

## Risk Assessment

### High Risk
1. **Output capture breaking console streaming**
   - Mitigation: Keep current capture approach, defer real-time streaming
2. **Log write failures during production**
   - Mitigation: Comprehensive error handling, fail explicitly

### Medium Risk
1. **Filesystem performance with many log files**
   - Mitigation: Day-level grouping limits files per directory
2. **Large responses causing memory issues**
   - Mitigation: Truncate response body > 10KB in logs

### Low Risk
1. **Timezone confusion (UTC vs local)**
   - Mitigation: Always use UTC, document clearly
2. **Header case sensitivity**
   - Mitigation: Use case-insensitive lookup, store original case

---

## Success Criteria

1. ✅ Every HTTP request generates a log file in `data/logs/YYYY/MM/DD/`
2. ✅ Log filename format: `YYYYMMDD-HHMM-SSμμμμμμ-{code}.md`
3. ✅ Logs contain all required sections with correct data
4. ✅ Dry-run mode returns HTML preview, no file written
5. ✅ Console output still visible during execution
6. ✅ All error scenarios (404, 500, timeout) logged correctly
7. ✅ Log write failures result in explicit 500 error
8. ✅ All tests pass without polluting `data/logs/`
9. ✅ Existing functionality unchanged (no regression)
10. ✅ Files sort correctly in filesystem (chronological order)

---

## Timeline Estimate

- **Phase 1**: 1-2 hours (Foundation)
- **Phase 2**: 2-3 hours (Formatting)
- **Phase 3**: 1 hour (Provider updates)
- **Phase 4**: 3-4 hours (Main integration - most complex)
- **Phase 5**: 3-4 hours (Testing)
- **Phase 6**: 1-2 hours (Validation)

**Total Estimated Time**: 11-16 hours

This can be executed iteratively, completing and testing each phase before moving to the next.
