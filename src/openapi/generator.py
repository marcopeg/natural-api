"""
OpenAPI generator - builds an OpenAPI 3.1 document from prompt files.
First iteration: list endpoints (paths + methods). Optionally include path params
and request body when defined in frontmatter/body validator.
"""
from pathlib import Path
from typing import Any, Dict, List

from src.prompts.loader import load_prompts, PromptMetadata
from src.prompts.body_validator import parse_body_schema
from src.prompts.router import DynamicRouter


def _path_parameters_from_route(route: str) -> List[Dict[str, Any]]:
    """Extract FastAPI-style path parameters from a route and return OpenAPI params."""
    import re
    params: List[Dict[str, Any]] = []
    for m in re.finditer(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::path)?\}", route):
        name = m.group(1)
        params.append({
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        })
    return params


def generate_openapi(prompts_dir: Path) -> Dict[str, Any] | Dict[str, Any]:
    """
    Generate OpenAPI 3.1 document or raise/return structured errors on conflicts.
    Returns a dict representing the OpenAPI JSON.
    """
    prompts = load_prompts(prompts_dir)

    # Validate for route conflicts: same method + same explicit path OR fallback collisions
    errors: List[Dict[str, Any]] = []

    # Collect explicit routes
    explicit_key_map: Dict[tuple[str, str], PromptMetadata] = {}
    # Collect fallback routes (GET /{filename})
    fallback_key_map: Dict[str, PromptMetadata] = {}

    for p in prompts:
        if p.route:
            key = (p.method.upper(), p.route)
            if key in explicit_key_map:
                errors.append({
                    "file": str(p.filepath),
                    "type": "route_conflict",
                    "message": f"Explicit route {key[0]} {key[1]} also defined by {explicit_key_map[key].filename}",
                })
            else:
                explicit_key_map[key] = p
        else:
            # fallback only supports GET /{filename}
            fname = p.filename
            if fname in fallback_key_map:
                errors.append({
                    "file": str(p.filepath),
                    "type": "route_conflict",
                    "message": f"Fallback route GET /{fname} also defined by {fallback_key_map[fname].filename}",
                })
            else:
                fallback_key_map[fname] = p

    # Conflict: explicit path equals a fallback path (GET /{filename})
    for (method, route), p in explicit_key_map.items():
        if method == "GET" and route.startswith("/"):
            r = route
            # If explicit route is exactly "/{filename}" (single segment), check collision
            if r.count("/") == 1:  # leading slash only
                fname = r[1:]
                if fname in fallback_key_map:
                    errors.append({
                        "file": str(p.filepath),
                        "type": "route_conflict",
                        "message": f"Explicit {method} {route} collides with fallback GET /{fname}",
                    })

    if errors:
        return {"errors": errors}

    # Build OpenAPI document
    # Use 3.0.x for broader Swagger UI compatibility
    openapi: Dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Codex API",
            "version": "1.0.0",
            "description": "Dynamic prompt-based AI API",
        },
        "paths": {},
    }

    # Use router to mirror matching logic, but we only need to enumerate paths
    router = DynamicRouter(prompts_dir)
    router.prompts = prompts

    # Build paths from explicit routes, then fallback filename routes
    for p in prompts:
        if p.route:
            path = p.route
            method = p.method.lower()
        else:
            # fallback: GET /{filename}
            path = f"/{p.filename}"
            method = "get"

        path_item = openapi["paths"].setdefault(path, {})
        # Provide a unique operationId to avoid validator complaints
        op_id = f"{method}_{path.strip('/').replace('/', '_') or 'root'}_{p.filename}"
        operation: Dict[str, Any] = {
            "summary": f"Prompt {p.filename}",
            "operationId": op_id,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {"text/plain": {"schema": {"type": "string"}}},
                },
                "404": {"description": "Not Found"},
                "500": {"description": "Internal Server Error"},
            },
        }
        # Parameters: from path definition
        if p.route:
            params = _path_parameters_from_route(p.route)
            if params:
                operation["parameters"] = params
        # Request body: v1 optional; include only if body_schema is provided
        if p.body_schema and p.method.upper() in ("POST", "PUT", "PATCH"):
            # Build properties and required from body schema using existing parser
            try:
                field_schemas = parse_body_schema(p.body_schema)
            except Exception:
                field_schemas = []
            properties: Dict[str, Any] = {}
            required: List[str] = []
            for fs in field_schemas:
                schema: Dict[str, Any] = {}
                if fs.type == 'string':
                    schema["type"] = "string"
                    if fs.min_length is not None:
                        schema["minLength"] = fs.min_length
                    if fs.max_length is not None:
                        schema["maxLength"] = fs.max_length
                    if fs.pattern:
                        schema["pattern"] = fs.pattern
                    if fs.enum:
                        schema["enum"] = fs.enum
                elif fs.type == 'number':
                    # Use 'number' for floats; constraints via minimum/maximum
                    schema["type"] = "number"
                    if fs.min is not None:
                        schema["minimum"] = fs.min
                    if fs.max is not None:
                        schema["maximum"] = fs.max
                elif fs.type == 'boolean':
                    schema["type"] = "boolean"
                # default and description
                if fs.default is not None:
                    schema["default"] = fs.default
                if fs.description:
                    schema["description"] = fs.description
                properties[fs.name] = schema
                if fs.required:
                    required.append(fs.name)

            op_schema: Dict[str, Any] = {"type": "object", "properties": properties}
            if required:
                op_schema["required"] = required
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": op_schema
                    }
                }
            }
        path_item[method] = operation

    return openapi
