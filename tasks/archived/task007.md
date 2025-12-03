# Goal

Expose a dynamically build openapi definition based on the available prompts and their configuration.

## Route

/openapi.json

## Steps

- load all prompts definitions
  (frontmatter)
- validate the correctness of all prompts
- validate that there are no conflict in the information 
  (like 2 prompts implementing the same route, or duplicated fields in the same prompt)
- if there are errors, produce a full detailed error reporting document in a 500 response (or is there a better http code for it?)
- if there are no errors, output the openapi copliant json document

---

Progress and Decisions

- OpenAPI Version: 3.1 (confirmed)
- Generation Strategy: On-demand per request (no caching yet)
- Modularity: Implement as a separate, easily toggled module; controlled via env flag (e.g., `OPENAPI_ENABLED`)
- Source of Truth: Only prompts from `data/prompts/` (same as router)
- Route Consistency: Use the same dynamic route-building logic as the router for OpenAPI paths
- Schema Representation: Align with existing body validator for clarity and OpenAPI compliance
- Success Output: Return a complete OpenAPI document describing the API surface

First Iteration Scope

- Primary Goal: Produce an OpenAPI 3.1 document that lists all available endpoints as defined by the prompt files (routes + methods).
- Nice-to-Have: Include parameter documentation (path params) and request body schemas where available from frontmatter/body validator.
- Out of Scope (for v1): Deep schema inference from prompt text, query parameter support, advanced constraints beyond existing validator fields.

Open Questions / Clarifications Needed

- Request Body Details: Should we extend schemas with constraints like `minLength`, `maximum`, `pattern`, `minItems`, etc., beyond current validator fields?
- Path Parameters Types: Default to `string`, or allow type hints in frontmatter? Support enums/patterns?
- Query Parameters: Not currently supported—should they be deferred or documented if introduced later?
- Success Response Schema: Document as `text/plain` universally, or allow per-prompt overrides in frontmatter?
- Error Responses: Document structured error formats for 404/408/500/503 in the OpenAPI spec?
- Conflict Semantics: Treat routes like `/greet/{name}` vs `/greet/{id}` as conflicts? How to handle explicit route vs filename fallback collisions (`/hi` vs `hi.md`)?
- Validation Handling: On any invalid prompt, fail the whole `/openapi.json` generation (500) or omit invalid prompts and proceed?
- Error Report Format: Confirm JSON structure with file path, type, message, and optional line numbers; return all errors or limit count?
- Metadata Defaults: Confirm top-level `info` fields (title, version, description) and whether they should be configurable via env.
- Model/Agent Exposure: Include per-endpoint `x-model` and `x-agent` extensions in the spec?
- Route Normalization: Treat trailing slashes uniformly per FastAPI conventions?
- Prompts Without Body: Omit `requestBody` entirely vs include an empty schema; avoid trying to infer from `${variables}` for now?
- Validation Timing: Run validations only when `/openapi.json` is requested (as decided), or also warn at startup?
- Env Flag Behavior: When disabled, should `/openapi.json` return 404 or 503?

Implementation Notes (planned)

- Add `src/openapi/generator.py` with `generate_openapi()` leveraging loader and router.
- Add `/openapi.json` in `src/main.py`, gated by `OPENAPI_ENABLED`.
- Use body validator structures to emit OpenAPI-compliant requestBody schemas.
- Return 500 with detailed error JSON when conflicts/validation issues are found; otherwise, return the OpenAPI JSON.