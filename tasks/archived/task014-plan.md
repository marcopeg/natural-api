# Task 014 Plan: Improve Logging Quality and Traceability

## Overview
Add request ID support with format `YYYYMMDD-hhmm-s{microtime}` for better traceability.

## Steps

### 1. ✅ Update timestamp utilities to generate request IDs
- Add `generate_request_id()` function in `src/logging/timestamp.py`
- Format: `YYYYMMDD-hhmm-s{microtime}` (e.g., `20251203-1905-30036009`)

### 2. ✅ Update logging context to handle request IDs
- Modify `LoggingContext` in `src/logging/context.py` to accept and store request_id
- Support custom request_id from `x-request-id` header
- Ensure file name always uses generated timestamp format

### 3. ✅ Update log entry model
- Add `request_id` field to `LogEntry` dataclass in `src/logging/models.py`
- Position it as the first field in the log table

### 4. ✅ Update formatters to include request ID
- Modify markdown formatter in `src/logging/formatter.py` to show request_id first
- Modify HTML formatter in `src/logging/html_formatter.py` to show request_id first

### 5. ✅ Update main.py to extract and pass request ID
- Extract `x-request-id` from request headers
- Generate request_id at the beginning of each request
- Pass request_id to LoggingContext
- Add `x-request-id` header to all responses (including dry-run)

### 6. ✅ Update tests
- Test request ID generation format
- Test custom request ID handling
- Test response headers include x-request-id
- Test log file naming remains consistent
- Test log formatting includes request_id

### 7. ✅ Run full test suite
- Execute `pytest tests/ -v` to ensure all tests pass
- Fix any issues that arise

## Acceptance Criteria
- ✅ Request ID generated at start of each request with format `YYYYMMDD-hhmm-s{microtime}`
- ✅ Log file named with generated timestamp + status code
- ✅ `x-request-id` header returned in all responses (including dry-run)
- ✅ Request ID is first field in log table
- ✅ Custom request ID from header is used in logs but not in filename
- ✅ All tests pass
