# Goal

Improve logging quality and traceability.

# RequestID

At the very beginning of a request, compute the `request_id` variable as:

```
# Template
YYYYMMDD-hhmm-s{microtime}

# Example
20251203-1905-30036009
```

# How to Use the RequestID

1. it is the name of the log file (with a suffix status code as it is now)
2. it should be added as `x-request-id` header in the data returned (even in dry-run)
3. it should be the first field of the log table

# Custom RequestID

The client can provide a custom request id via `x-request-id` header, in such a case the user-provided value should be used in all circumstances but the name of the log file that stays true to the templatem `YYYYMMDD-hhmm-s{microtime}` to guarantee that it can be sorted.