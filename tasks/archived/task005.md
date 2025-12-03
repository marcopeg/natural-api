# Goal

Expand the dynamic prompt frontmatter to accept the key "body" that describes how to parse the request's JSON body for variable values that can be used in the prompt's body via `${body.fieldName}` syntax.

## Overview

Add support for request body validation using OpenAPI-compatible schema definitions in the frontmatter. The implementation should be modular, standards-compliant, and designed to facilitate future OpenAPI specification generation.

## Example Usage

```markdown
---
verb: POST
route: /user/{name}
body:
  prompt:
    type: string
    description: The instruction to execute
    required: true
    minLength: 5
    maxLength: 500
  repeat:
    type: number
    description: Number of times to repeat the action
    required: true
    min: 1
    max: 3
    maxDecimals: 0
  tone:
    type: string
    description: Response tone preference
    required: false
    default: friendly
    enum: [friendly, professional, casual]
---

Do whatever the user "${route.name}" wants:
${body.prompt}

Use a ${body.tone:neutral} tone.
Do it ${body.repeat} times.
```

## Variable Syntax Clarification

To avoid conflicts between route parameters and body fields:
- **Route parameters**: `${route.paramName}`
- **Body fields**: `${body.fieldName}`
- **Defaults supported**: `${body.fieldName:defaultValue}`

**Error handling:**
- If a body field duplicates a route parameter name, return `500 Internal Server Error` with detailed configuration error message
- If verb is not POST/PUT/PATCH but body schema is defined, return `500 Internal Server Error` indicating configuration mistake

## Supported Types

### 1. `string`
- **Validation properties**:
  - `required`: boolean (default: false)
  - `default`: string value
  - `minLength`: integer
  - `maxLength`: integer
  - `pattern`: regex string (e.g., `^[A-Z][a-z]+$`)
  - `enum`: array of allowed string values
  - `description`: string (for future OpenAPI generation)

### 2. `number`
- **Validation properties**:
  - `required`: boolean (default: false)
  - `default`: number value
  - `min`: number (inclusive minimum)
  - `max`: number (inclusive maximum)
  - `maxDecimals`: integer (0 for integers, null/omitted for any decimal precision)
  - `description`: string (for future OpenAPI generation)

### 3. `boolean`
- **Validation properties**:
  - `required`: boolean (default: false)
  - `default`: boolean value
  - `description`: string (for future OpenAPI generation)

**Not supported in this phase:**
- Nested objects
- Arrays
- `null` type
- Custom types

## Implementation Requirements

### Library Choice: **Pydantic**

**Rationale:**
1. Native dynamic model creation via `create_model()`
2. Exports JSON Schema (foundation for OpenAPI)
3. Rich validation with excellent error messages
4. Supports all required validation rules
5. Industry standard in Python API development
6. Aligns with future OpenAPI generation task

### Module Structure (SRP Compliant)

Create modular implementation with clear separation of concerns:

```
src/prompts/
  ├── body_validator.py    # NEW: Body validation logic
  │   ├── BodyFieldSchema  # Dataclass: parsed field definition
  │   ├── build_pydantic_model()  # Convert YAML to Pydantic model
  │   ├── validate_body()  # Validate request body
  │   └── format_validation_errors()  # Format errors for response
  ├── loader.py            # MODIFY: Parse body from frontmatter
  ├── variables.py         # MODIFY: Support ${route.x} and ${body.x}
  └── executor.py          # MODIFY: Pass validated body to variable substitution
```

### Content-Type Handling

- **Accept**: `application/json` only
- **Reject** non-JSON with `415 Unsupported Media Type`
- **Validate**: JSON syntax before schema validation

### Validation Behavior

1. **Complete validation**: Collect ALL errors before responding (not fail-fast)
2. **No type coercion**: Strict typing (e.g., `"123"` is invalid for number field)
3. **Extra fields**: Return `422 Unprocessable Entity` with detailed error listing unexpected fields
4. **Missing required fields**: Include in error list with resolution hint
5. **Empty body**: If schema expects required fields, return validation errors

### Error Response Format

**HTTP Status Code**: `422 Unprocessable Entity` (standard for validation errors)

**Response structure**:
```json
{
  "error": "Request Validation Failed",
  "details": [
    {
      "field": "body.repeat",
      "error": "value must be between 1 and 3",
      "received": 5,
      "expected": "number in range [1, 3]"
    },
    {
      "field": "body.prompt",
      "error": "field is required but missing",
      "expected": "string with length 5-500"
    },
    {
      "field": "body.unknown_field",
      "error": "unexpected field not in schema",
      "suggestion": "remove this field or update prompt schema"
    }
  ],
  "hint": "Review the API documentation for correct body schema"
}
```

**Verbose by design**: Provide maximum detail since this is primarily a development tool. Future task may add production mode with reduced verbosity.

### Configuration Error Handling

Return `500 Internal Server Error` for prompt configuration issues:
- Body schema defined but verb is GET/DELETE
- Duplicate field names between route parameters and body fields
- Invalid regex pattern in schema
- Invalid enum definition

Example response:
```json
{
  "error": "Prompt Configuration Error",
  "file": "data/prompts/user-profile.md",
  "message": "Field 'name' defined in both route parameters and body schema",
  "resolution": "Rename one of the fields to avoid conflict"
}
```

## OpenAPI Considerations

Each body field should support standard OpenAPI properties for future schema generation:
- `description`: Human-readable field description
- `example`: Example value (future enhancement)
- `deprecated`: Mark field as deprecated (future enhancement)

The schema format in frontmatter should directly map to OpenAPI 3.0 `requestBody.content.application/json.schema.properties`.

## Testing Strategy

### Unit Tests (`tests/test_body_validator.py`)
- Valid requests with all type combinations
- Missing required fields
- Invalid types (string sent for number)
- Boundary violations (min/max, minLength/maxLength)
- Regex pattern matching/failing
- Enum validation
- Extra fields in request
- Empty body when schema expects data
- Default values application
- maxDecimals validation (integers vs floats)

### Integration Tests (`tests/test_main.py`)
- Add tests for body validation in API endpoints
- Test error response format
- Test Content-Type handling
- Test configuration error scenarios

### E2E Tests (`tests/test_e2e.py`)
Create test prompts under `/test/xxx` routes:
- `/test/body-simple` - Basic string/number validation
- `/test/body-defaults` - Test default values
- `/test/body-validation` - Test min/max/length constraints
- `/test/body-enum` - Test enum validation
- `/test/body-errors` - Test multiple validation errors
- `/test/body-config-error` - Test configuration conflicts

**Coverage goals:**
- Happy path with valid bodies
- Common validation mistakes
- Configuration errors
- Don't over-engineer; focus on real-world scenarios

## Performance Considerations

- **No caching**: Parse and validate on each request (performance not critical)
- **No startup compilation**: Build Pydantic models on-demand per request
- **No body size limits**: Can be added in future task if needed

## Security

- **Input sanitization**: Use Pydantic's built-in validation to prevent injection
- **No complexity limits**: No nesting support eliminates deep schema attacks
- **No sensitive data handling**: Can be added in future task

## Future Tasks Dependencies

This implementation sets foundation for:
1. **OpenAPI Generation**: Reuse Pydantic models to generate full OpenAPI 3.0 spec
2. **Enhanced Types**: Add array, object, custom types
3. **Advanced Validation**: Cross-field validation, conditional schemas
4. **Performance**: Add caching, schema pre-compilation
5. **Documentation UI**: Auto-generate API docs from prompts

## Implementation Checklist

- [ ] Add `pydantic` to `requirements.txt`
- [ ] Create `src/prompts/body_validator.py` module
- [ ] Update `src/prompts/loader.py` to parse body schema
- [ ] Update `src/prompts/variables.py` to support `${route.x}` and `${body.x}`
- [ ] Update `src/prompts/executor.py` to validate body and inject variables
- [ ] Update `src/main.py` to handle body in POST/PUT/PATCH requests
- [ ] Create comprehensive unit tests
- [ ] Add integration tests
- [ ] Create E2E test prompts
- [ ] Update documentation
- [ ] Run full test suite: `pytest tests/ -v`