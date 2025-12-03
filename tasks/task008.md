# Goal

Support multi-project and multi-users requests with isolated scopes for the prompts and the agent's data workspace.

# Specifications

## Headers

### Project Identifier (`x-project-id`)
- **Header name**: Case-insensitive (e.g., `X-Project-Id`, `x-project-id`, `X-PROJECT-ID` all work)
- **Value format**: Case-insensitive, regex `[a-zA-Z0-9-]+`
- **Default**: `default` (if header not provided)
- **Behavior**: 
  - Project must exist in `/data/projects/{ProjectID}/` (case-insensitive match)
  - If project doesn't exist: HTTP 412 Precondition Failed

### User Identifier (`x-user-id`)
- **Header name**: Case-insensitive
- **Value format**: Case-insensitive, regex `[a-zA-Z0-9-]+`
- **Default**: `anonymous` (if header not provided)
- **Behavior**: 
  - User workspace auto-created if needed (see below)
  - No authentication/authorization - header is trusted

## Folder Structure

```
data/
├── projects/
│   ├── default/
│   │   ├── prompts/           # Prompt files for default project
│   │   └── AGENTS.md          # Optional agent configuration
│   └── test/
│       ├── prompts/           # Prompt files for test project
│       └── AGENTS.md          # Optional agent configuration
└── storage/
    ├── anonymous/
    │   ├── default/           # Workspace for anonymous user on default project
    │   │   └── AGENTS.md      # Symlink to projects/default/AGENTS.md (if exists)
    │   └── test/              # Workspace for anonymous user on test project
    │       └── AGENTS.md      # Symlink to projects/test/AGENTS.md (if exists)
    └── {UserID}/
        └── {ProjectID}/       # Workspace for specific user on specific project
            └── AGENTS.md      # Symlink to projects/{ProjectID}/AGENTS.md (if exists)
```

### Projects Folder

**Location**: `/data/projects/{ProjectID}/`

**Contains**:
- `prompts/` - Required directory with `*.md` prompt files
- `AGENTS.md` - Optional agent configuration file

**Validation**:
- Project directory must exist before accepting requests
- Empty prompts folder results in empty API surface (no error)

### Storage Folder (User Workspaces)

**Location**: `/data/storage/{UserID}/{ProjectID}/`

**Purpose**: AI workspace for file creation/modification, completely isolated per user+project

**Auto-creation Logic** (executed on every request):
1. Check if project exists in `/data/projects/{ProjectID}/` - if not, return HTTP 412
2. Create `/data/storage/{UserID}/` if doesn't exist
3. Create `/data/storage/{UserID}/{ProjectID}/` if doesn't exist
4. Check if `/data/projects/{ProjectID}/AGENTS.md` exists
   - If yes: Create symlink at `/data/storage/{UserID}/{ProjectID}/AGENTS.md` → `../../../projects/{ProjectID}/AGENTS.md`
   - If symlink already exists: Do nothing
   - If no AGENTS.md in project: Skip symlink creation

**Important**: The symlink check happens on every request, so if a project adds AGENTS.md later, it will be linked automatically.

# Request Flow

## Dynamic Route Handler (`/{path:path}`)

**New Flow**:

1. **Extract Headers** (case-insensitive):
   - `x-project-id` → normalize to lowercase, default to `"default"`
   - `x-user-id` → normalize to lowercase, default to `"anonymous"`

2. **Validate Project**:
   - Check if `/data/projects/{project_id}/` exists
   - If not: HTTP 412 Precondition Failed
     ```json
     {
       "error": "Precondition Failed",
       "message": "Project '{project_id}' does not exist",
       "requested_project": "{project_id}",
       "available_projects": ["default", "test"]
     }
     ```

3. **Load Prompts**:
   - Initialize `DynamicRouter` with `/data/projects/{project_id}/prompts/`
   - Load and match route (existing logic)
   - If no match: HTTP 404 (existing behavior)

4. **Setup User Workspace**:
   - Ensure `/data/storage/{user_id}/` exists (create if needed)
   - Ensure `/data/storage/{user_id}/{project_id}/` exists (create if needed)
   - Check for `/data/projects/{project_id}/AGENTS.md`
     - If exists and symlink doesn't exist: Create symlink
     - Use relative path for symlink: `../../../projects/{project_id}/AGENTS.md`

5. **Execute Prompt**:
   - Initialize `PromptExecutor` with workspace: `/data/storage/{user_id}/{project_id}/`
   - Execute prompt (existing logic)
   - Return result

## OpenAPI Endpoints

### `/openapi.json?project={ProjectID}`

**Query Parameter**:
- `project` - Optional, default to `"default"`
- Case-insensitive, regex `[a-zA-Z0-9-]+`

**Behavior**:
1. Extract and normalize `project` parameter
2. Check if `/data/projects/{project_id}/` exists
   - If not: HTTP 404
     ```json
     {
       "error": "Not Found",
       "message": "Project '{project_id}' does not exist",
       "requested_project": "{project_id}",
       "available_projects": ["default", "test"]
     }
     ```
3. Load prompts from `/data/projects/{project_id}/prompts/`
4. Generate OpenAPI document (existing logic)

**Enhancement**: If possible, add project selector dropdown in the OpenAPI UI (nice-to-have, not required)

### `/openapi?project={ProjectID}`

Same logic as `/openapi.json` but serves Swagger UI.

# Implementation

See [task008-plan.md](./task008-plan.md) for detailed implementation plan.

# Edge Cases & Error Handling

## Case Sensitivity
- All project IDs, user IDs, and header names are case-insensitive
- Normalize to lowercase immediately after extraction
- File system lookups use normalized values

## Invalid Characters
- Reject project/user IDs that don't match `[a-zA-Z0-9-]+`
- Return HTTP 400 Bad Request with clear error message

## Symlink Edge Cases
- If symlink already exists: Do nothing (don't error)
- If symlink points to wrong location: Recreate it (or document as known limitation)
- If AGENTS.md is deleted from project: Symlink remains (orphaned) but doesn't cause errors

## Empty Projects
- Project with no prompts: Returns empty API surface (no error)
- Project with only AGENTS.md: Empty API surface, but AGENTS.md is linked

## Concurrent Requests
- Multiple requests to same user+project: No locking, rely on filesystem atomicity
- Race condition on workspace creation: mkdir with exist_ok=True handles this

## HTTP Status Codes
- **400 Bad Request**: Invalid project/user ID format
- **404 Not Found**: Prompt not found OR project not found in OpenAPI endpoints
- **412 Precondition Failed**: Project doesn't exist in dynamic routes
- **422 Unprocessable Entity**: Request body validation errors (existing)
- **503 Service Unavailable**: Provider not available (existing)

# Testing Strategy

## Test Scope
- All tests target project `test` and user `test`
- Headers: `{"x-project-id": "test", "x-user-id": "test"}`
- Verify functionality works end-to-end with multi-tenancy

## Test Coverage
1. Default project/user behavior (no headers)
2. Explicit project/user (with headers)
3. Case-insensitive headers
4. Non-existent project (412 for routes, 404 for OpenAPI)
5. Workspace auto-creation
6. AGENTS.md symlink creation
7. All existing functionality still works with new structure

## No Need To Test
- Multiple different projects (only test with `test` project)
- Multiple different users (only test with `test` user)
- Backwards compatibility (no migration needed)
- Security/authorization (out of scope)
- Performance/scalability (out of scope)

# Success Criteria

1. ✅ All requests can specify project via `x-project-id` header (case-insensitive)
2. ✅ All requests can specify user via `x-user-id` header (case-insensitive)
3. ✅ Prompts are loaded from `/data/projects/{project_id}/prompts/`
4. ✅ AI workspace is `/data/storage/{user_id}/{project_id}/`
5. ✅ AGENTS.md is symlinked when present in project
6. ✅ Non-existent project returns HTTP 412 (routes) or 404 (OpenAPI)
7. ✅ OpenAPI endpoints support `?project=` query parameter
8. ✅ All existing tests pass with headers targeting `test` project/user
9. ✅ Default project/user behavior works (no headers = default/anonymous)
10. ✅ Complete data isolation between users and projects


