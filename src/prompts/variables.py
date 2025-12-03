"""
Variable substitution module - replaces ${var} and ${var:default} patterns
"""
import re
import logging


logger = logging.getLogger(__name__)


# Regex pattern to match ${variable} or ${variable:default}
# Also supports namespaced variables: ${route.name}, ${body.field}
# Group 1: namespace (optional: 'route' or 'body')
# Group 2: variable name
# Group 3: default value (optional, after colon)
VARIABLE_PATTERN = re.compile(
    r'\$\{(?:(route|body)\.)?([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]*))?\}'
)


def substitute_variables(
    template: str,
    route_params: dict[str, str] | None = None,
    body_params: dict[str, str] | None = None,
) -> str:
    """
    Replace variable placeholders in template with values from parameters.
    
    Supports three syntaxes:
    - ${route.variable} - route parameter substitution
    - ${body.variable} - body field substitution
    - ${route.variable:default} or ${body.variable:default} - with defaults
    
    Legacy syntax (deprecated but supported):
    - ${variable} - searches route_params, then body_params
    - ${variable:default} - with default value
    
    Args:
        template: String containing variable placeholders
        route_params: Dictionary of route parameter name -> value mappings
        body_params: Dictionary of body field name -> value mappings
        
    Returns:
        String with variables substituted
        
    Examples:
        >>> substitute_variables("Hello ${route.name}!", route_params={"name": "Alice"})
        'Hello Alice!'
        
        >>> substitute_variables("Do: ${body.task}", body_params={"task": "code"})
        'Do: code'
        
        >>> substitute_variables("Tone: ${body.tone:neutral}", body_params={})
        'Tone: neutral'
    """
    route_params = route_params or {}
    body_params = body_params or {}
    
    def replace_match(match: re.Match) -> str:
        namespace = match.group(1)  # 'route', 'body', or None
        var_name = match.group(2)
        default_value = match.group(3)
        
        # Handle namespaced variables
        if namespace == 'route':
            if var_name in route_params:
                value = route_params[var_name]
                logger.debug(f"Substituting ${{route.{var_name}}} with '{value}'")
                return value
        elif namespace == 'body':
            if var_name in body_params:
                value = str(body_params[var_name])
                logger.debug(f"Substituting ${{body.{var_name}}} with '{value}'")
                return value
        else:
            # Legacy syntax: check route_params first, then body_params
            if var_name in route_params:
                value = route_params[var_name]
                logger.warning(
                    f"Using deprecated syntax ${{{var_name}}}. "
                    f"Use ${{route.{var_name}}} for route parameters."
                )
                return value
            elif var_name in body_params:
                value = str(body_params[var_name])
                logger.warning(
                    f"Using deprecated syntax ${{{var_name}}}. "
                    f"Use ${{body.{var_name}}} for body fields."
                )
                return value
        
        # Use default if provided
        if default_value is not None:
            prefix = f"{namespace}." if namespace else ""
            logger.debug(
                f"Substituting ${{{prefix}{var_name}}} with default '{default_value}'"
            )
            return default_value
        
        # No value and no default - use empty string
        prefix = f"{namespace}." if namespace else ""
        logger.debug(
            f"Substituting ${{{prefix}{var_name}}} with empty string (not found)"
        )
        return ""
    
    result = VARIABLE_PATTERN.sub(replace_match, template)
    return result
