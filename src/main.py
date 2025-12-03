import re
from fastapi import HTTPException, Request

# Regex for validating project/user IDs
PROJECT_USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+$')

# Paths that should be ignored by the dynamic handler
# These are standard browser/infrastructure requests that will never be prompts
IGNORED_PATHS = {
    "/favicon.ico",           # Browser favicon request
    "/robots.txt",            # Search engine crawlers
    "/sitemap.xml",           # SEO sitemap
    "/apple-touch-icon.png",  # iOS home screen icon
    "/apple-touch-icon-precomposed.png",
    "/.well-known",           # ACME, security.txt, etc. (prefix match)
    "/.git",                  # Git repository (prefix match)
    "/.env",                  # Environment files (prefix match)
    "/.vscode",               # Editor config (prefix match)
    "/.idea",                 # IDE config (prefix match)
}

def _parse_dry_flag(value: str | None) -> bool | None:
    """
    Parse dry-run flag from query/header value.
    
    Returns:
        True if dry-run enabled, False if disabled, None if not set/invalid
    """
    if value is None:
        return None
    if value == "":  # Header present with no value
        return True
    normalized = value.lower()
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    return None  # Invalid value treated as not set

def extract_header(request: Request, name: str, default: str) -> str:
    """
    Extract header value with case-insensitive lookup, normalization, and validation.
    """
    value = None
    for header_name, header_value in request.headers.items():
        if header_name.lower() == name.lower():
            value = header_value
            break
    if value is None:
        value = default
    normalized = value.lower()
    if not PROJECT_USER_ID_PATTERN.match(normalized):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": f"Invalid {name}: must match [a-zA-Z0-9-]+",
                "received": value,
                "header": name
            }
        )
    return normalized

def validate_project_exists(project_id: str):
    """
    Validate that project exists, raise 412 if not.
    """
    from src.config import Config
    if not Config.project_exists(project_id):
        available = Config.list_available_projects()
        raise HTTPException(
            status_code=412,
            detail={
                "error": "Precondition Failed",
                "message": f"Project '{project_id}' does not exist",
                "requested_project": project_id,
                "available_projects": available
            }
        )

def setup_user_workspace(user_id: str, project_id: str):
    """
    Setup user workspace directory.
    
    Creates the user storage directory and the user+project workspace directory.
    No AGENTS.md symlinks are created; prompt composition reads AGENTS.md directly
    from the project directory when executing prompts.
    """
    from src.config import Config
    from pathlib import Path
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get paths
    workspace_path = Config.get_user_workspace_dir(user_id, project_id)
    
    # Create user directory if needed
    user_dir = Config.get_storage_dir() / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured user directory exists: {user_dir}")
    
    # Create user+project workspace if needed
    workspace_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured workspace exists: {workspace_path}")
    
    return workspace_path

"""
Codex API Server - Phase 3
FastAPI server with dynamic prompt-based routing
"""
import logging
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse, HTMLResponse, Response
from src.config import config
from src.providers.factory import ProviderFactory, ProviderNotFoundError
from src.prompts.router import DynamicRouter
from src.prompts.executor import PromptExecutor
from src.prompts.body_validator import (
    parse_body_schema,
    validate_body_schema,
    build_pydantic_model,
    validate_request_body,
    PromptConfigurationError,
)
from src.openapi.generator import generate_openapi
from src.logging.context import RequestLogContext
from src.logging.writer import write_log
from src.logging.formatter import format_log_markdown
from src.logging.html_formatter import format_log_html
from src.logging.timestamp import generate_request_id, generate_timestamp


# Setup logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Disable FastAPI's built-in /openapi.json and /docs to use our custom generator
app = FastAPI(
    title="Codex API", 
    version="0.3.0",
    docs_url=None,  # Disable built-in /docs
    redoc_url=None,  # Disable built-in /redoc
    openapi_url=None  # Disable built-in /openapi.json
)


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Codex API",
        "version": "0.3.0",
        "phase": "3 - Dynamic Prompt-Based Routing",
        "description": "REST API wrapper for AI CLI tools with dynamic prompt-based routing",
        "endpoints": {
            "/": "API information",
            "/<dynamic>": "Dynamic routes based on prompts in data/projects/{project}/prompts/*.md"
        },
        "provider": config.AI_PROVIDER,
        "available_providers": ProviderFactory.list_providers(),
        "projects_dir": str(config.get_projects_dir())
    }


@app.get("/openapi.json")
async def openapi_document(request: Request, project: str = "default"):
    """
    Dynamically generate OpenAPI 3.1 document from project's prompt files.
    
    Query Parameters:
        project: Project ID (default: "default")
    """
    if not config.OPENAPI_ENABLED:
        raise HTTPException(status_code=404, detail={
            "error": "Not Found",
            "message": "OpenAPI endpoint is disabled",
        })
    
    # Normalize and validate project parameter
    project_id = project.lower()
    
    # Validate format
    if not PROJECT_USER_ID_PATTERN.match(project_id):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": f"Invalid project ID: must match [a-zA-Z0-9-]+",
                "received": project,
            }
        )
    
    # Check project exists
    if not config.project_exists(project_id):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Not Found",
                "message": f"Project '{project_id}' does not exist",
                "requested_project": project_id,
                "available_projects": config.list_available_projects()
            }
        )
    
    # Get project's prompts directory
    prompts_dir = config.get_project_prompts_dir(project_id)
    result = generate_openapi(prompts_dir)
    if "errors" in result:
        return JSONResponse(status_code=500, content=result)
    return JSONResponse(content=result)


@app.get("/openapi")
async def openapi_swagger_ui(project: str = "default"):
        """Serve Swagger UI that consumes the dynamic /openapi.json."""
        if not config.OPENAPI_ENABLED:
                raise HTTPException(status_code=404, detail={
                        "error": "Not Found",
                        "message": "OpenAPI endpoint is disabled",
                })
        
        # Normalize and validate project parameter
        project_id = project.lower()
        
        # Validate format
        if not PROJECT_USER_ID_PATTERN.match(project_id):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Bad Request",
                    "message": f"Invalid project ID: must match [a-zA-Z0-9-]+",
                    "received": project,
                }
            )
        
        # Check project exists
        if not config.project_exists(project_id):
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Not Found",
                    "message": f"Project '{project_id}' does not exist",
                    "requested_project": project_id,
                    "available_projects": config.list_available_projects()
                }
            )
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Codex API – Swagger UI (Project: {project_id})</title>
            <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
            <script>
                window.onload = () => {{
                    const ui = SwaggerUIBundle({{
                        url: '/openapi.json?project={project_id}',
                        dom_id: '#swagger-ui',
                        presets: [SwaggerUIBundle.presets.apis],
                        layout: 'BaseLayout'
                    }});
                    window.ui = ui;
                }};
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def dynamic_prompt_handler(request: Request, path: str):
    """
    Handle all dynamic prompt-based routes.
    
    This endpoint matches any path not handled by static routes above.
    It loads prompts from the data/prompts directory and executes matching ones.
    """
    # Check if path should be ignored (standard browser/infrastructure requests)
    full_path = f"/{path}" if path else "/"
    
    # Check exact matches first
    if full_path in IGNORED_PATHS:
        raise HTTPException(status_code=404, detail={
            "error": "Not Found",
            "message": f"Resource not available"
        })
    
    # Check prefix matches (for paths like .well-known/*, .git/*, etc.)
    for ignored in IGNORED_PATHS:
        if full_path.startswith(ignored + "/") or full_path == ignored:
            raise HTTPException(status_code=404, detail={
                "error": "Not Found",
                "message": f"Resource not available"
            })
    
    # Initialize logging context early
    method = request.method
    
    # Generate timestamp once at the very beginning (used for request_id and log file)
    request_timestamp = generate_timestamp()
    
    # Extract or generate request ID
    # Client can provide custom request_id, but filename will still use generated timestamp
    custom_request_id = request.headers.get('x-request-id')
    file_request_id = generate_request_id(request_timestamp)  # Use same timestamp
    display_request_id = custom_request_id if custom_request_id else file_request_id
    
    log_ctx = RequestLogContext(
        method=method,
        path=full_path,
        project_id="default",  # Will be updated
        user_id="anonymous",   # Will be updated
        headers=dict(request.headers),
        request_id=display_request_id,
        timestamp=request_timestamp
    )
    
    try:
        # Extract and validate headers
        project_id = extract_header(request, "x-project-id", "default")
        user_id = extract_header(request, "x-user-id", "anonymous")
        
        # Update logging context with resolved IDs
        log_ctx.project_id = project_id
        log_ctx.user_id = user_id
        
        # Extract dry-run flags (for precedence: prompt > header > query)
        dry_from_query = request.query_params.get('dry')
        dry_query = _parse_dry_flag(dry_from_query)
        
        dry_from_header = request.headers.get('x-dry')
        dry_header = _parse_dry_flag(dry_from_header)
        
        logger.info(f"Dynamic route request: {method} {full_path} (project={project_id}, user={user_id})")
        
        # Validate project exists
        validate_project_exists(project_id)
        
        # Get project's prompts directory
        prompts_dir = config.get_project_prompts_dir(project_id)
        
        # Initialize router and load prompts
        router = DynamicRouter(prompts_dir)
        router.load_prompts()
        
        # Match route
        match = router.match_route(method, full_path)
        
        if not match:
            logger.warning(f"No prompt found for {method} {full_path}")
            error_detail = {
                "error": "Not Found",
                "message": f"No prompt found for route: {method} {full_path}",
                "available_prompts": len(router.prompts)
            }
            log_ctx.set_response(json.dumps(error_detail), 404)
            # Write log before raising exception
            try:
                write_log(log_ctx.to_log_entry(), file_request_id)
            except IOError as log_err:
                logger.error(f"Failed to write log: {log_err}")
            raise HTTPException(status_code=404, detail=error_detail, headers={"x-request-id": display_request_id})
        
        logger.info(f"Matched prompt: {match.prompt.filename} (type={match.match_type}, params={match.path_params})")
        log_ctx.set_prompt(match.prompt.filename)
        
        # Determine final dry-run value (prompt > header > query > default)
        dry_run = match.prompt.dry if match.prompt.dry is not None else (
            dry_header if dry_header is not None else (
                dry_query if dry_query is not None else False
            )
        )
        
        if dry_run:
            logger.info(f"Dry-run mode enabled for {match.prompt.filename}")
            
            # DRY-RUN MODE: Return HTML preview instead of executing
            # Build mock command
            provider_name = match.prompt.agent if match.prompt.agent else config.AI_PROVIDER
            provider = ProviderFactory.create(
                provider_name=provider_name,
                workspace_dir=config.get_workspace_dir(),
                timeout=config.TIMEOUT_SECONDS
            )
            
            # Execute in dry-run mode to get command
            workspace_dir = setup_user_workspace(user_id, project_id)
            executor = PromptExecutor(workspace_dir=workspace_dir, timeout=config.TIMEOUT_SECONDS)
            # Record cwd for log metadata
            log_ctx.set_cwd(str(workspace_dir))
            dry_result = executor.execute(
                match.prompt,
                route_params=match.path_params,
                body_params=None,
                dry_run=True,
                project_id=project_id
            )
            
            log_ctx.command = dry_result.command
            log_ctx.status_code = 200
            
            # Generate log content (omit AI Output and Response sections for dry-run)
            log_entry = log_ctx.to_log_entry()
            log_markdown = format_log_markdown(log_entry, is_dry_run=True)
            
            # Detect client type from Accept header
            accept_header = request.headers.get("accept", "")
            prefers_html = "text/html" in accept_header or "application/xhtml" in accept_header
            
            # Browsers send Accept: text/html, curl/postman send */* or text/plain
            if prefers_html:
                # Browser: return HTML
                html = format_log_html(log_markdown)
                return HTMLResponse(content=html, status_code=200, headers={"x-request-id": display_request_id})
            else:
                # CLI/API clients: return plain markdown
                return Response(content=log_markdown, media_type="text/plain", status_code=200, headers={"x-request-id": display_request_id})
        
        # NORMAL MODE: Execute and log
        
        # Handle request body validation if schema is defined
        body_params = None
        if match.prompt.body_schema:
            # Validate configuration first
            try:
                # Check method compatibility
                if method.upper() not in ['POST', 'PUT', 'PATCH']:
                    raise PromptConfigurationError(
                        f"Body schema defined but method is '{method}'. "
                        f"Body validation only supported for POST, PUT, PATCH requests."
                    )
                
                # Parse and validate schema
                field_schemas = parse_body_schema(match.prompt.body_schema)
                route_param_names = list(match.path_params.keys()) if match.path_params else []
                validate_body_schema(field_schemas, route_param_names, method)
                
                # Build Pydantic model
                pydantic_model = build_pydantic_model(field_schemas)
                
            except PromptConfigurationError as e:
                logger.error(f"Prompt configuration error in {match.prompt.filename}: {e}")
                error_detail = {
                    "error": "Prompt Configuration Error",
                    "file": str(match.prompt.filepath),
                    "message": str(e),
                    "resolution": "Fix the prompt file configuration"
                }
                log_ctx.set_response(json.dumps(error_detail), 500)
                try:
                    write_log(log_ctx.to_log_entry(), file_request_id)
                except IOError as log_err:
                    logger.error(f"Failed to write log: {log_err}")
                raise HTTPException(status_code=500, detail=error_detail, headers={"x-request-id": display_request_id})
            
            # Validate Content-Type
            content_type = request.headers.get('content-type', '')
            if not content_type.startswith('application/json'):
                error_detail = {
                    "error": "Unsupported Media Type",
                    "message": "Content-Type must be application/json",
                    "received": content_type or "none",
                    "expected": "application/json"
                }
                log_ctx.set_response(json.dumps(error_detail), 415)
                try:
                    write_log(log_ctx.to_log_entry(), file_request_id)
                except IOError as log_err:
                    logger.error(f"Failed to write log: {log_err}")
                raise HTTPException(status_code=415, detail=error_detail, headers={"x-request-id": display_request_id})
            
            # Parse request body
            try:
                raw_body = await request.body()
                if not raw_body:
                    request_body = {}
                else:
                    request_body = json.loads(raw_body)
            except json.JSONDecodeError as e:
                error_detail = {
                    "error": "Bad Request",
                    "message": f"Invalid JSON in request body: {str(e)}",
                }
                log_ctx.set_response(json.dumps(error_detail), 400)
                try:
                    write_log(log_ctx.to_log_entry(), file_request_id)
                except IOError as log_err:
                    logger.error(f"Failed to write log: {log_err}")
                raise HTTPException(status_code=400, detail=error_detail, headers={"x-request-id": display_request_id})
            
            # Validate request body
            validated_data, validation_errors = validate_request_body(request_body, pydantic_model)
            
            if validation_errors:
                error_detail = {
                    "error": "Request Validation Failed",
                    "details": validation_errors,
                    "hint": "Review the API documentation for correct body schema"
                }
                log_ctx.set_response(json.dumps(error_detail), 422)
                try:
                    write_log(log_ctx.to_log_entry(), file_request_id)
                except IOError as log_err:
                    logger.error(f"Failed to write log: {log_err}")
                raise HTTPException(status_code=422, detail=error_detail, headers={"x-request-id": display_request_id})
            
            # Convert validated data to body_params (all values as strings for substitution)
            body_params = {k: str(v) if v is not None else "" for k, v in validated_data.items()}
            logger.debug(f"Validated body params: {body_params}")
        
        # Setup user workspace (creates dirs and symlinks as needed)
        workspace_dir = setup_user_workspace(user_id, project_id)
        # Record cwd for log metadata
        log_ctx.set_cwd(str(workspace_dir))
        
        # Initialize executor
        executor = PromptExecutor(
            workspace_dir=workspace_dir,
            timeout=config.TIMEOUT_SECONDS
        )
        
        # Check provider availability first
        provider_name = match.prompt.agent if match.prompt.agent else config.AI_PROVIDER
        provider = ProviderFactory.create(
            provider_name=provider_name,
            workspace_dir=workspace_dir,
            timeout=config.TIMEOUT_SECONDS
        )
        
        if not provider.is_available():
            error_detail = {
                "error": "Service Unavailable",
                "message": f"AI provider '{provider.name}' is not installed or not available",
                "provider": provider.name
            }
            log_ctx.set_response(json.dumps(error_detail), 503)
            try:
                write_log(log_ctx.to_log_entry(), file_request_id)
            except IOError as log_err:
                logger.error(f"Failed to write log: {log_err}")
            raise HTTPException(status_code=503, detail=error_detail, headers={"x-request-id": display_request_id})
        
        # Execute prompt
        result = executor.execute(
            match.prompt,
            route_params=match.path_params,
            body_params=body_params,
            dry_run=dry_run,
            project_id=project_id
        )
        
        # Update log context with execution result
        log_ctx.set_execution_result(result)
        
        # Handle timeout
        if result.returncode == 124:
            log_ctx.set_error("timeout")
            error_detail = {
                "error": "Request Timeout",
                "message": result.error_message,
                "provider": provider.name,
                "stderr": result.stderr
            }
            log_ctx.set_response(json.dumps(error_detail), 408)
            try:
                write_log(log_ctx.to_log_entry(), file_request_id)
            except IOError as log_err:
                logger.error(f"Failed to write log: {log_err}")
            raise HTTPException(status_code=408, detail=error_detail, headers={"x-request-id": display_request_id})
        
        # Handle execution failure
        if not result.success:
            log_ctx.set_error("execution_failed")
            error_detail = {
                "error": "Internal Server Error",
                "message": result.error_message or "AI execution failed",
                "provider": provider.name,
                "returncode": result.returncode,
                "stderr": result.stderr
            }
            log_ctx.set_response(json.dumps(error_detail), 500)
            try:
                write_log(log_ctx.to_log_entry(), file_request_id)
            except IOError as log_err:
                logger.error(f"Failed to write log: {log_err}")
            raise HTTPException(status_code=500, detail=error_detail, headers={"x-request-id": display_request_id})
        
        # Success - update log and write before returning
        log_ctx.set_response(result.stdout, 200)
        
        try:
            log_path = write_log(log_ctx.to_log_entry(), file_request_id)
            logger.debug(f"Request logged to: {log_path}")
        except IOError as e:
            logger.error(f"Failed to write log: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Logging Failed",
                    "message": f"Failed to write request log: {str(e)}"
                },
                headers={"x-request-id": display_request_id}
            )
        
        # Return raw stdout as plain text
        return PlainTextResponse(content=result.stdout, headers={"x-request-id": display_request_id})
        
    except ProviderNotFoundError as e:
        error_detail = {
            "error": "Service Unavailable",
            "message": str(e),
            "available_providers": ProviderFactory.list_providers()
        }
        log_ctx.set_response(json.dumps(error_detail), 503)
        try:
            write_log(log_ctx.to_log_entry(), file_request_id)
        except:
            pass
        raise HTTPException(status_code=503, detail=error_detail, headers={"x-request-id": display_request_id})
    except HTTPException as e:
        # HTTP exceptions already logged above, just re-raise
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(f"Unexpected error in dynamic route handler: {e}")
        error_detail = {
            "error": "Internal Server Error",
            "message": f"Unexpected error: {str(e)}"
        }
        log_ctx.set_error("unexpected_error")
        log_ctx.set_response(json.dumps(error_detail), 500)
        try:
            write_log(log_ctx.to_log_entry(), file_request_id)
        except:
            pass
        raise HTTPException(status_code=500, detail=error_detail, headers={"x-request-id": display_request_id})
