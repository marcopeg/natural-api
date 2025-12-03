"""
Request body validation using Pydantic.

This module provides:
- Schema parsing from YAML frontmatter
- Dynamic Pydantic model creation
- Request body validation
- Configuration validation
- Error formatting for API responses
"""

from dataclasses import dataclass
from typing import Any
import re
import logging
from pydantic import (
    create_model,
    Field,
    ValidationError,
    field_validator,
    BaseModel,
)

logger = logging.getLogger(__name__)


class PromptConfigurationError(Exception):
    """Raised when prompt configuration is invalid."""
    pass


@dataclass
class BodyFieldSchema:
    """Represents a single field in the body schema."""
    name: str
    type: str  # 'string', 'number', 'boolean'
    required: bool = False
    default: Any = None
    description: str | None = None
    
    # String-specific
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    enum: list[str] | None = None
    
    # Number-specific
    min: float | None = None
    max: float | None = None
    max_decimals: int | None = None


def parse_body_schema(body_yaml: dict[str, Any]) -> list[BodyFieldSchema]:
    """
    Parse body schema from YAML frontmatter.
    
    Args:
        body_yaml: Dictionary from frontmatter 'body' key
        
    Returns:
        List of BodyFieldSchema objects
        
    Raises:
        PromptConfigurationError: If schema is malformed
    """
    if not isinstance(body_yaml, dict):
        raise PromptConfigurationError("Body schema must be a dictionary")
    
    schemas = []
    for field_name, field_config in body_yaml.items():
        if not isinstance(field_config, dict):
            raise PromptConfigurationError(
                f"Field '{field_name}' configuration must be a dictionary"
            )
        
        field_type = field_config.get('type')
        if not field_type:
            raise PromptConfigurationError(
                f"Field '{field_name}' missing required 'type' property"
            )
        
        if field_type not in ['string', 'number', 'boolean']:
            raise PromptConfigurationError(
                f"Field '{field_name}' has unsupported type '{field_type}'. "
                f"Supported types: string, number, boolean"
            )
        
        schema = BodyFieldSchema(
            name=field_name,
            type=field_type,
            required=field_config.get('required', False),
            default=field_config.get('default'),
            description=field_config.get('description'),
            min_length=field_config.get('minLength'),
            max_length=field_config.get('maxLength'),
            pattern=field_config.get('pattern'),
            enum=field_config.get('enum'),
            min=field_config.get('min'),
            max=field_config.get('max'),
            max_decimals=field_config.get('maxDecimals'),
        )
        
        schemas.append(schema)
    
    return schemas


def validate_body_schema(
    schemas: list[BodyFieldSchema],
    route_params: list[str] | None = None,
    method: str | None = None,
) -> None:
    """
    Validate body schema configuration for errors.
    
    Args:
        schemas: List of field schemas to validate
        route_params: List of route parameter names (to check for duplicates)
        method: HTTP method (to ensure POST/PUT/PATCH)
        
    Raises:
        PromptConfigurationError: If configuration is invalid
    """
    # Check method compatibility
    if method and schemas:
        if method.upper() not in ['POST', 'PUT', 'PATCH']:
            raise PromptConfigurationError(
                f"Body schema defined but method is '{method}'. "
                f"Body validation only supported for POST, PUT, PATCH requests."
            )
    
    # Check for duplicate field names with route params
    if route_params:
        route_param_set = set(route_params)
        for schema in schemas:
            if schema.name in route_param_set:
                raise PromptConfigurationError(
                    f"Field '{schema.name}' defined in both route parameters and body schema. "
                    f"Rename one to avoid conflict."
                )
    
    # Validate regex patterns
    for schema in schemas:
        if schema.pattern:
            try:
                re.compile(schema.pattern)
            except re.error as e:
                raise PromptConfigurationError(
                    f"Field '{schema.name}' has invalid regex pattern '{schema.pattern}': {e}"
                )
    
    # Validate enum values
    for schema in schemas:
        if schema.enum is not None:
            if not isinstance(schema.enum, list) or len(schema.enum) == 0:
                raise PromptConfigurationError(
                    f"Field '{schema.name}' has invalid enum. Must be non-empty list."
                )


def build_pydantic_model(schemas: list[BodyFieldSchema]) -> type[BaseModel]:
    """
    Build a dynamic Pydantic model from field schemas.
    
    Args:
        schemas: List of field schemas
        
    Returns:
        Dynamically created Pydantic model class
    """
    from pydantic import ConfigDict
    
    fields = {}
    validators = {}
    
    for schema in schemas:
        # Determine Python type
        if schema.type == 'string':
            python_type = str
        elif schema.type == 'number':
            python_type = float
        elif schema.type == 'boolean':
            python_type = bool
        else:
            raise ValueError(f"Unsupported type: {schema.type}")
        
        # Build field constraints
        constraints = {}
        
        if schema.type == 'string':
            if schema.min_length is not None:
                constraints['min_length'] = schema.min_length
            if schema.max_length is not None:
                constraints['max_length'] = schema.max_length
            if schema.pattern:
                constraints['pattern'] = schema.pattern
        
        elif schema.type == 'number':
            if schema.min is not None:
                constraints['ge'] = schema.min
            if schema.max is not None:
                constraints['le'] = schema.max
        
        # Handle default and required
        if schema.default is not None:
            default_value = schema.default
        elif not schema.required:
            default_value = None
            python_type = python_type | None
        else:
            default_value = ...  # Required field marker
        
        # Add description
        if schema.description:
            constraints['description'] = schema.description
        
        # Create field
        if constraints or schema.enum:
            if schema.enum:
                # For enum, we need to validate against the list
                constraints['description'] = (
                    constraints.get('description', '') + 
                    f" (allowed values: {', '.join(map(str, schema.enum))})"
                ).strip()
            fields[schema.name] = (python_type, Field(default=default_value, **constraints))
        else:
            fields[schema.name] = (python_type, default_value)
        
        # Add custom validators for enum and maxDecimals
        if schema.enum:
            validator_name = f'validate_{schema.name}_enum'
            def make_enum_validator(field_name: str, allowed_values: list):
                def validator(cls, v):
                    if v is not None and v not in allowed_values:
                        raise ValueError(
                            f"must be one of {allowed_values}, got '{v}'"
                        )
                    return v
                validator.__name__ = validator_name
                return field_validator(field_name)(validator)
            
            validators[validator_name] = make_enum_validator(schema.name, schema.enum)
        
        if schema.max_decimals is not None and schema.type == 'number':
            validator_name = f'validate_{schema.name}_decimals'
            def make_decimal_validator(field_name: str, max_dec: int):
                def validator(cls, v):
                    if v is None:
                        return v
                    # For integers (max_decimals=0), check if value is an integer
                    if max_dec == 0:
                        if not isinstance(v, int) or isinstance(v, bool):
                            # If it's a float, check if it has no decimal part
                            if isinstance(v, float):
                                if v != int(v):
                                    raise ValueError(
                                        f"maximum 0 decimal places allowed (must be integer)"
                                    )
                        return v
                    # Check decimal places
                    decimal_str = str(v)
                    if '.' in decimal_str:
                        decimal_places = len(decimal_str.split('.')[1])
                        if decimal_places > max_dec:
                            raise ValueError(
                                f"maximum {max_dec} decimal places allowed, got {decimal_places}"
                            )
                    return v
                validator.__name__ = validator_name
                return field_validator(field_name)(validator)
            
            validators[validator_name] = make_decimal_validator(schema.name, schema.max_decimals)
    
    # Create the model with validators
    model = create_model(
        'DynamicBodyModel',
        **fields,
        __validators__=validators
    )
    
    return model


def validate_request_body(
    body: dict[str, Any],
    model: type[BaseModel],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    """
    Validate request body against Pydantic model.
    
    Args:
        body: Raw request body dictionary
        model: Pydantic model to validate against
        
    Returns:
        Tuple of (validated_data, errors)
        - If valid: (validated_data_dict, None)
        - If invalid: (None, list_of_error_dicts)
    """
    try:
        validated = model(**body)
        return validated.model_dump(), None
    except ValidationError as e:
        errors = format_validation_errors(e, body)
        return None, errors


def format_validation_errors(
    validation_error: ValidationError,
    received_body: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Format Pydantic validation errors for API response.
    
    Args:
        validation_error: Pydantic ValidationError
        received_body: The body that was sent in the request
        
    Returns:
        List of error dictionaries with field, error, received, expected
    """
    errors = []
    
    for error in validation_error.errors():
        field_path = '.'.join(str(loc) for loc in error['loc'])
        field_name = f"body.{field_path}"
        
        error_type = error['type']
        error_msg = error['msg']
        
        # Extract received value
        received_value = received_body.get(error['loc'][0]) if len(error['loc']) > 0 else None
        
        # Format user-friendly error
        if error_type == 'missing':
            formatted_error = {
                'field': field_name,
                'error': 'field is required but missing',
                'expected': _format_expected(error),
            }
        elif error_type == 'string_type':
            formatted_error = {
                'field': field_name,
                'error': 'must be a string',
                'received': received_value,
                'expected': 'string',
            }
        elif error_type in ['float_type', 'int_type']:
            formatted_error = {
                'field': field_name,
                'error': 'must be a number',
                'received': received_value,
                'expected': 'number',
            }
        elif error_type == 'bool_type':
            formatted_error = {
                'field': field_name,
                'error': 'must be a boolean',
                'received': received_value,
                'expected': 'boolean (true or false)',
            }
        elif error_type == 'extra_forbidden':
            formatted_error = {
                'field': field_name,
                'error': 'unexpected field not in schema',
                'received': received_value,
                'suggestion': 'remove this field or update prompt schema',
            }
        else:
            # Generic error formatting
            formatted_error = {
                'field': field_name,
                'error': error_msg,
                'received': received_value,
            }
        
        errors.append(formatted_error)
    
    return errors


def _format_expected(error: dict) -> str:
    """Format expected value description from Pydantic error."""
    ctx = error.get('ctx', {})
    error_type = error['type']
    
    if 'min_length' in ctx and 'max_length' in ctx:
        return f"string with length {ctx['min_length']}-{ctx['max_length']}"
    elif 'min_length' in ctx:
        return f"string with minimum length {ctx['min_length']}"
    elif 'max_length' in ctx:
        return f"string with maximum length {ctx['max_length']}"
    elif 'ge' in ctx and 'le' in ctx:
        return f"number in range [{ctx['ge']}, {ctx['le']}]"
    elif 'ge' in ctx:
        return f"number >= {ctx['ge']}"
    elif 'le' in ctx:
        return f"number <= {ctx['le']}"
    else:
        return error.get('msg', 'valid value')
