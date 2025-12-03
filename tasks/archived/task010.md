# Goal

Log all HTTP requests to the API in the data folder, capturing request details, AI execution, and responses for observability and debugging.

# Architecture

## Storage Location
- Logs are stored relative to `WORKSPACE_DIR` (configurable, defaults to `./data`)
- Log path: `{WORKSPACE_DIR}/logs/{year}/{month}/{day}/YYYYMMDD-HHMM-SSμμμμμμ-{status_code}.md`
- Example: `data/logs/2025/12/03/20251203-1415-30123456-200.md`

## Implementation Approach
- **Synchronous file I/O**: Acceptable for current scale, avoids async complexity
- **Integrated logging**: Implement within `dynamic_prompt_handler` in `src/main.py`
- **Real-time output preservation**: Continue streaming AI output to console while capturing for logs
- **Error handling**: Fail explicitly (500 error) if log writing fails

# Log Folder Structure

```
{WORKSPACE_DIR}/logs/
└── {YYYY}/              # 4-digit year (e.g., 2025)
    └── {MM}/            # 2-digit month (e.g., 12)
        └── {DD}/        # 2-digit day (e.g., 03)
            ├── 20251203-1415-30123456-200.md  # Success
            ├── 20251203-1535-78901234-404.md  # Not found
            ├── 20251203-1540-34567890-500.md  # Error
            └── ...
```

**Rationale for day-level grouping**: 
- Current request volume doesn't justify hour-level nesting
- Easier navigation with fewer directory levels
- Still prevents excessive files in single directory

**Filename Format**: `YYYYMMDD-HHMM-SSμμμμμμ-{status_code}.md`
- Date portion: `YYYYMMDD` (e.g., `20251203`)
- Hyphen separator for readability
- Time portion: `HHMM` (e.g., `1415` for 2:15 PM)
- Hyphen separator for readability
- Seconds with microseconds: `SSμμμμμμ` (e.g., `30123456` for 30.123456 seconds)
- Hyphen separator before status code
- Status code suffix: `{status_code}` (e.g., `200`, `404`, `500`)
- **Maintains correct filesystem sorting**: Alphabetical sort = chronological sort
- UTC timezone for consistency

# Log File Structure

The log file is a markdown document with strict structure for machine readability and human-friendly formatting.

## Template

```markdown
# YYYY/MM/DD HH:MM:SS.μμμμμμ UTC

| Key       | Value                                      |
|-----------|--------------------------------------------|
| Timestamp | YYYY/MM/DD HH:MM:SS.μμμμμμ UTC           |
| Status    | {HTTP status code}                         |
| Method    | {HTTP method}                              |
| Path      | {request path}                             |
| Project   | {resolved project ID}                      |
| User      | {resolved user ID}                         |
| Prompt    | {prompt filename}                          |
| Duration  | {duration}ms                               |

## Command

\`\`\`bash
# The actual CLI command executed by the provider
{command}
\`\`\`

## Headers

| Key           | Value                     |
|---------------|---------------------------|
| X-Project-Id  | {value}                   |
| X-User-Id     | {value}                   |
| X-Dry         | {value or empty}          |

## AI Output

\`\`\`text
{AI stdout/stderr captured during execution}
\`\`\`

## Response

\`\`\`json
{HTTP response body if JSON, or text preview}
\`\`\`
```

## Field Specifications

### Timestamp
- **Format**: `YYYY/MM/DD HH:MM:SS.μμμμμμ UTC`
- **Example**: `2025/12/03 14:15:30.123456 UTC`
- **Timezone**: Always UTC
- **Microsecond separator**: Period (`.`) for readability in title, vs full numeric in filename

### Status
- HTTP status code: `200`, `404`, `408`, `500`, `503`, etc.
- Logged for all requests (success and failure)

### Method & Path
- Original HTTP method and path from request
- Examples: `GET /hi`, `POST /greet/Alice`

### Project & User (Resolved Values)
- **Resolved** means: If header absent, log the default value used
- Examples:
  - Header `X-Project-Id: myproject` → log `myproject`
  - No header → log `default` (the default value)
  - Header `X-User-Id: alice` → log `alice`
  - No header → log `anonymous` (the default value)

### Prompt
- Filename of matched prompt file (e.g., `greet.md`)
- For 404s (no match), log `none` or `not-found`

### Duration
- **Format**: `{milliseconds}ms`
- **Examples**: `1000ms`, `250ms`, `5000ms`
- **Measured from**: Start of request handler to response generation
- **Precision**: Milliseconds (no fractional ms needed)

### Command
- The actual CLI command executed by the provider
- Same format as shown in dry-run mode
- Example: `codex exec --model gpt-5.1-codex-mini "Generate greeting for Alice"`
- Format for maximum readability (multi-line if needed)
- For errors before execution (e.g., 404), log `none` or the failed attempt

### Headers
- **Only log these headers**: `X-Project-Id`, `X-User-Id`, `X-Dry`
- Do not log other headers (`Authorization`, `User-Agent`, etc.)
- Show actual values received (not normalized/lowercased)

### AI Output
- Capture complete stdout/stderr from AI provider execution
- Must preserve real-time console streaming (user still sees live output)
- For errors (timeout, execution failure), capture whatever output exists
- For 404s (no prompt), section is empty or states "No execution"

### Response
- The actual HTTP response body sent to client
- If JSON, format as JSON for readability
- If text/plain, include preview (truncate if very long)
- For errors, include the error detail object

# Dry-Run Integration

When dry-run mode is enabled (via prompt frontmatter, `X-Dry` header, or `?dry=true` query param):

## Behavior
1. **Do NOT write log file to disk**
2. **Return log content as response** - format depends on client type
3. **HTTP Status**: Return `200 OK`

## Content-Type Negotiation

The response format is determined by the `Accept` header:

### CLI/API Clients (curl, Postman, scripts)
- **Accept**: `*/*`, `text/plain`, or no `text/html`
- **Response**: `text/plain; charset=utf-8` (markdown source)
- **Use case**: Machine-readable, copy-pasteable, grep-able

### Browser Clients
- **Accept**: Contains `text/html` or `application/xhtml`
- **Response**: `text/html; charset=utf-8` (styled HTML)
- **Use case**: Human-readable preview with formatting

## HTML Response Format
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Dry-Run Log Preview</title>
    <style>
        body { font-family: monospace; white-space: pre-wrap; padding: 20px; }
        h1 { color: #333; }
        .section { margin: 20px 0; }
        .command { background: #f4f4f4; padding: 10px; border-left: 3px solid #333; }
    </style>
</head>
<body>
{log markdown converted to HTML or rendered as-is}
</body>
</html>
```

## Dry-Run Log Content Differences
- **Duration**: Show as `0ms` or `N/A` (no execution)
- **Command Section**: Show the command that **would** be executed, formatted for maximum readability
- **AI Output Section**: Omit entirely (or show "Not executed (dry-run mode)")
- **Response Section**: Show "Dry-run - no AI execution"

# Error Logging

## All Requests Are Logged
Log **every request** regardless of outcome:
- `200` - Success
- `404` - No matching prompt found
- `400` - Bad request (validation errors)
- `408` - Request timeout
- `500` - Internal server error
- `503` - Service unavailable

## Partial Logs for Failures
- If AI execution crashes mid-stream, log whatever was captured
- If timeout occurs, log output up to timeout point
- Mark incomplete logs in Duration field: `1000ms (timeout)` or `500ms (error)`

## Log Write Failures
- If log directory creation fails → Return `500` error
- If log file write fails → Return `500` error with explicit message
- **Do NOT silently fail**: User must know logging failed
- Error message example: `"Failed to write request log: {error details}"`

# Implementation Checklist

## Code Changes
- [ ] Add log directory creation utility in `src/config.py`
- [ ] Create log formatter module: `src/logging/formatter.py`
- [ ] Create log writer module: `src/logging/writer.py`
- [ ] Integrate logging into `dynamic_prompt_handler` in `src/main.py`
- [ ] Capture AI output while preserving console streaming
- [ ] Handle dry-run mode: return HTML instead of logging
- [ ] Add error handling for log write failures

## Testing
- [ ] Unit tests for log formatter (timestamp, filename, markdown structure)
- [ ] Unit tests for log writer (path generation, content writing)
- [ ] Unit tests for dry-run HTML generation
- [ ] **Do NOT create integration/E2E tests that write actual log files**
- [ ] **Do NOT pollute `data/logs/` with test fixtures**
- [ ] Mock file system operations in tests

## Configuration
## Timestamp Generation
```python
from datetime import datetime, timezone

# For filename: readable format with hyphens
timestamp = datetime.now(timezone.utc)
filename_ts = (
    timestamp.strftime("%Y%m%d-%H%M-") +  # Date and time with separators
    timestamp.strftime("%S") +            # Seconds
    f"{timestamp.microsecond:06d}"        # Microseconds (6 digits)
)
# Result: "20251203-1415-30123456"

# For title: human-readable with microseconds
title_ts = timestamp.strftime("%Y/%m/%d %H:%M:%S") + f".{timestamp.microsecond:06d} UTC"
# Result: "2025/12/03 14:15:30.123456 UTC"

# For folder path
folder_path = timestamp.strftime("%Y/%m/%d")
# Result: "2025/12/03"
```esult: "2025/12/03 14:15:30.123456 UTC"

# For folder path
folder_path = timestamp.strftime("%Y/%m/%d")
# Result: "2025/12/03"
```

## Duration Measurement
```python
import time

start_time = time.time()
# ... execute request ...
duration_ms = int((time.time() - start_time) * 1000)
# Format: f"{duration_ms}ms"
```

## AI Output Capture
- Currently, output streams to console via provider execution
- Need to capture stdout/stderr while still displaying it
- Consider using `subprocess` with real-time tee to both console and buffer
- Or modify provider to accept output callback/stream handler

## Dry-Run HTML Response
```python
from fastapi.responses import HTMLResponse

if dry_run:
    log_content = generate_log_markdown(...)
    html = render_log_as_html(log_content)
    return HTMLResponse(content=html, status_code=200)
```

# Future Enhancements (Out of Scope)

- [ ] Async file I/O with `aiofiles`
- [ ] Background task queue for logging
- [ ] Log query endpoint: `GET /logs?date=2025-12-03&status=500`
- [ ] Automatic log retention/rotation
- [ ] Structured logging to JSON (in addition to markdown)
- [ ] Log aggregation for containerized deployments
- [ ] Sensitive data redaction (tokens, PII)