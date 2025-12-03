"""
Unit tests for body validator module
"""
import pytest
from pydantic import ValidationError
from src.prompts.body_validator import (
    parse_body_schema,
    validate_body_schema,
    build_pydantic_model,
    validate_request_body,
    format_validation_errors,
    PromptConfigurationError,
    BodyFieldSchema,
)


class TestParseBodySchema:
    """Test schema parsing from YAML"""
    
    def test_parse_simple_string_field(self):
        """Test parsing a simple string field"""
        yaml = {
            "name": {
                "type": "string",
                "required": True
            }
        }
        schemas = parse_body_schema(yaml)
        assert len(schemas) == 1
        assert schemas[0].name == "name"
        assert schemas[0].type == "string"
        assert schemas[0].required is True
    
    def test_parse_number_field_with_constraints(self):
        """Test parsing number field with min/max"""
        yaml = {
            "age": {
                "type": "number",
                "min": 0,
                "max": 120,
                "maxDecimals": 0
            }
        }
        schemas = parse_body_schema(yaml)
        assert schemas[0].type == "number"
        assert schemas[0].min == 0
        assert schemas[0].max == 120
        assert schemas[0].max_decimals == 0
    
    def test_parse_string_with_length_constraints(self):
        """Test parsing string with length constraints"""
        yaml = {
            "username": {
                "type": "string",
                "minLength": 3,
                "maxLength": 20
            }
        }
        schemas = parse_body_schema(yaml)
        assert schemas[0].min_length == 3
        assert schemas[0].max_length == 20
    
    def test_parse_string_with_pattern(self):
        """Test parsing string with regex pattern"""
        yaml = {
            "email": {
                "type": "string",
                "pattern": "^[a-z]+@[a-z]+\\.[a-z]+$"
            }
        }
        schemas = parse_body_schema(yaml)
        assert schemas[0].pattern == "^[a-z]+@[a-z]+\\.[a-z]+$"
    
    def test_parse_string_with_enum(self):
        """Test parsing string with enum values"""
        yaml = {
            "color": {
                "type": "string",
                "enum": ["red", "green", "blue"]
            }
        }
        schemas = parse_body_schema(yaml)
        assert schemas[0].enum == ["red", "green", "blue"]
    
    def test_parse_boolean_field(self):
        """Test parsing boolean field"""
        yaml = {
            "active": {
                "type": "boolean",
                "default": True
            }
        }
        schemas = parse_body_schema(yaml)
        assert schemas[0].type == "boolean"
        assert schemas[0].default is True
    
    def test_parse_multiple_fields(self):
        """Test parsing multiple fields"""
        yaml = {
            "name": {"type": "string", "required": True},
            "age": {"type": "number", "min": 0},
            "active": {"type": "boolean"}
        }
        schemas = parse_body_schema(yaml)
        assert len(schemas) == 3
        names = [s.name for s in schemas]
        assert "name" in names
        assert "age" in names
        assert "active" in names
    
    def test_parse_field_with_description(self):
        """Test parsing field with description"""
        yaml = {
            "prompt": {
                "type": "string",
                "description": "The instruction to execute"
            }
        }
        schemas = parse_body_schema(yaml)
        assert schemas[0].description == "The instruction to execute"
    
    def test_parse_invalid_not_dict(self):
        """Test parsing raises error for non-dict input"""
        with pytest.raises(PromptConfigurationError, match="must be a dictionary"):
            parse_body_schema("not a dict")
    
    def test_parse_field_config_not_dict(self):
        """Test parsing raises error for non-dict field config"""
        yaml = {"name": "string"}
        with pytest.raises(PromptConfigurationError, match="must be a dictionary"):
            parse_body_schema(yaml)
    
    def test_parse_missing_type(self):
        """Test parsing raises error for missing type"""
        yaml = {"name": {"required": True}}
        with pytest.raises(PromptConfigurationError, match="missing required 'type'"):
            parse_body_schema(yaml)
    
    def test_parse_unsupported_type(self):
        """Test parsing raises error for unsupported type"""
        yaml = {"data": {"type": "array"}}
        with pytest.raises(PromptConfigurationError, match="unsupported type"):
            parse_body_schema(yaml)


class TestValidateBodySchema:
    """Test schema configuration validation"""
    
    def test_validate_method_compatibility_post(self):
        """Test that POST method is compatible with body schema"""
        schemas = [BodyFieldSchema(name="field", type="string")]
        # Should not raise
        validate_body_schema(schemas, method="POST")
    
    def test_validate_method_compatibility_put(self):
        """Test that PUT method is compatible with body schema"""
        schemas = [BodyFieldSchema(name="field", type="string")]
        validate_body_schema(schemas, method="PUT")
    
    def test_validate_method_compatibility_patch(self):
        """Test that PATCH method is compatible with body schema"""
        schemas = [BodyFieldSchema(name="field", type="string")]
        validate_body_schema(schemas, method="PATCH")
    
    def test_validate_method_incompatible_get(self):
        """Test that GET method raises error with body schema"""
        schemas = [BodyFieldSchema(name="field", type="string")]
        with pytest.raises(PromptConfigurationError, match="Body schema defined but method is 'GET'"):
            validate_body_schema(schemas, method="GET")
    
    def test_validate_duplicate_field_names(self):
        """Test error when route param duplicates body field"""
        schemas = [BodyFieldSchema(name="name", type="string")]
        route_params = ["name", "id"]
        with pytest.raises(PromptConfigurationError, match="defined in both route parameters and body schema"):
            validate_body_schema(schemas, route_params, "POST")
    
    def test_validate_invalid_regex(self):
        """Test error for invalid regex pattern"""
        schemas = [BodyFieldSchema(name="email", type="string", pattern="[invalid(")]
        with pytest.raises(PromptConfigurationError, match="invalid regex pattern"):
            validate_body_schema(schemas, method="POST")
    
    def test_validate_empty_enum(self):
        """Test error for empty enum list"""
        schemas = [BodyFieldSchema(name="color", type="string", enum=[])]
        with pytest.raises(PromptConfigurationError, match="invalid enum"):
            validate_body_schema(schemas, method="POST")
    
    def test_validate_enum_not_list(self):
        """Test error for non-list enum"""
        schemas = [BodyFieldSchema(name="color", type="string", enum="red")]
        with pytest.raises(PromptConfigurationError, match="invalid enum"):
            validate_body_schema(schemas, method="POST")


class TestBuildPydanticModel:
    """Test Pydantic model creation"""
    
    def test_build_simple_string_model(self):
        """Test building model with required string field"""
        schemas = [BodyFieldSchema(name="name", type="string", required=True)]
        model = build_pydantic_model(schemas)
        
        # Valid data
        instance = model(name="Alice")
        assert instance.name == "Alice"
        
        # Missing required field
        with pytest.raises(ValidationError):
            model()
    
    def test_build_optional_string_model(self):
        """Test building model with optional string field"""
        schemas = [BodyFieldSchema(name="name", type="string", required=False)]
        model = build_pydantic_model(schemas)
        
        # Can omit optional field
        instance = model()
        assert instance.name is None
    
    def test_build_string_with_default(self):
        """Test building model with default value"""
        schemas = [BodyFieldSchema(name="role", type="string", default="guest")]
        model = build_pydantic_model(schemas)
        
        instance = model()
        assert instance.role == "guest"
    
    def test_build_string_with_length_constraints(self):
        """Test string length validation"""
        schemas = [BodyFieldSchema(
            name="username",
            type="string",
            required=True,
            min_length=3,
            max_length=10
        )]
        model = build_pydantic_model(schemas)
        
        # Valid
        model(username="alice")
        
        # Too short
        with pytest.raises(ValidationError):
            model(username="ab")
        
        # Too long
        with pytest.raises(ValidationError):
            model(username="verylongusername")
    
    def test_build_string_with_pattern(self):
        """Test string pattern validation"""
        schemas = [BodyFieldSchema(
            name="code",
            type="string",
            required=True,
            pattern="^[A-Z]{3}$"
        )]
        model = build_pydantic_model(schemas)
        
        # Valid
        model(code="ABC")
        
        # Invalid
        with pytest.raises(ValidationError):
            model(code="abc")
        with pytest.raises(ValidationError):
            model(code="ABCD")
    
    def test_build_string_with_enum(self):
        """Test string enum validation"""
        schemas = [BodyFieldSchema(
            name="color",
            type="string",
            required=True,
            enum=["red", "green", "blue"]
        )]
        model = build_pydantic_model(schemas)
        
        # Valid
        model(color="red")
        
        # Invalid
        with pytest.raises(ValidationError):
            model(color="yellow")
    
    def test_build_number_field(self):
        """Test number field validation"""
        schemas = [BodyFieldSchema(name="age", type="number", required=True)]
        model = build_pydantic_model(schemas)
        
        # Valid
        model(age=25)
        model(age=25.5)
        
        # Pydantic coerces strings to numbers by default (acceptable for dev tool)
        result = model(age="25")
        assert result.age == 25.0
    
    def test_build_number_with_range(self):
        """Test number range validation"""
        schemas = [BodyFieldSchema(
            name="score",
            type="number",
            required=True,
            min=0,
            max=100
        )]
        model = build_pydantic_model(schemas)
        
        # Valid
        model(score=50)
        model(score=0)
        model(score=100)
        
        # Out of range
        with pytest.raises(ValidationError):
            model(score=-1)
        with pytest.raises(ValidationError):
            model(score=101)
    
    def test_build_number_with_max_decimals(self):
        """Test maxDecimals validation"""
        schemas = [BodyFieldSchema(
            name="price",
            type="number",
            required=True,
            max_decimals=2
        )]
        model = build_pydantic_model(schemas)
        
        # Valid
        model(price=10.99)
        model(price=10.5)
        model(price=10)
        
        # Too many decimals
        with pytest.raises(ValidationError):
            model(price=10.999)
    
    def test_build_integer_field(self):
        """Test integer field (maxDecimals=0)"""
        schemas = [BodyFieldSchema(
            name="count",
            type="number",
            required=True,
            max_decimals=0
        )]
        model = build_pydantic_model(schemas)
        
        # Valid - integers or floats that are whole numbers
        model(count=5)
        model(count=5.0)
        
        # Has decimals
        with pytest.raises(ValidationError):
            model(count=5.5)
    
    def test_build_boolean_field(self):
        """Test boolean field validation"""
        schemas = [BodyFieldSchema(name="active", type="boolean", required=True)]
        model = build_pydantic_model(schemas)
        
        # Valid
        model(active=True)
        model(active=False)
        
        # Pydantic coerces common boolean representations (acceptable for dev tool)
        result = model(active="true")
        assert result.active is True
    
    def test_build_multiple_fields(self):
        """Test model with multiple fields"""
        schemas = [
            BodyFieldSchema(name="name", type="string", required=True),
            BodyFieldSchema(name="age", type="number", min=0, max=120),
            BodyFieldSchema(name="active", type="boolean", default=True)
        ]
        model = build_pydantic_model(schemas)
        
        instance = model(name="Alice", age=30)
        assert instance.name == "Alice"
        assert instance.age == 30
        assert instance.active is True


class TestValidateRequestBody:
    """Test request body validation"""
    
    def test_validate_valid_body(self):
        """Test validation with valid body"""
        schemas = [BodyFieldSchema(name="name", type="string", required=True)]
        model = build_pydantic_model(schemas)
        
        body = {"name": "Alice"}
        validated, errors = validate_request_body(body, model)
        
        assert errors is None
        assert validated == {"name": "Alice"}
    
    def test_validate_with_defaults(self):
        """Test validation applies defaults"""
        schemas = [
            BodyFieldSchema(name="name", type="string", default="Anonymous"),
            BodyFieldSchema(name="active", type="boolean", default=True)
        ]
        model = build_pydantic_model(schemas)
        
        body = {}
        validated, errors = validate_request_body(body, model)
        
        assert errors is None
        assert validated["name"] == "Anonymous"
        assert validated["active"] is True
    
    def test_validate_missing_required_field(self):
        """Test validation fails for missing required field"""
        schemas = [BodyFieldSchema(name="prompt", type="string", required=True)]
        model = build_pydantic_model(schemas)
        
        body = {}
        validated, errors = validate_request_body(body, model)
        
        assert validated is None
        assert errors is not None
        assert len(errors) > 0
        assert any("body.prompt" in err["field"] for err in errors)
    def test_validate_type_mismatch(self):
        """Test validation with type that gets coerced"""
        schemas = [BodyFieldSchema(name="age", type="number", required=True)]
        model = build_pydantic_model(schemas)
        
        # Pydantic will coerce "25" to 25.0 (acceptable for dev tool)
        body = {"age": "25"}
        validated, errors = validate_request_body(body, model)
        
        assert validated is not None
        assert validated["age"] == 25.0
        
        # But truly invalid strings will fail
        body = {"age": "not_a_number"}
        validated, errors = validate_request_body(body, model)
        assert validated is None
        assert errors is not None
        assert errors is not None
    
    def test_validate_constraint_violation(self):
        """Test validation fails for constraint violation"""
        schemas = [BodyFieldSchema(name="count", type="number", min=1, max=10, required=True)]
        model = build_pydantic_model(schemas)
        
        body = {"count": 100}
        validated, errors = validate_request_body(body, model)
        
        assert validated is None
        assert errors is not None
    
    def test_validate_multiple_errors(self):
        """Test validation collects multiple errors"""
        schemas = [
            BodyFieldSchema(name="field1", type="string", required=True, min_length=5),
            BodyFieldSchema(name="field2", type="number", required=True, min=1, max=10)
        ]
        model = build_pydantic_model(schemas)
        
        body = {"field1": "hi", "field2": 100}  # Both invalid
        validated, errors = validate_request_body(body, model)
        
        assert validated is None
        assert errors is not None
        assert len(errors) >= 2


class TestFormatValidationErrors:
    """Test error formatting"""
    
    def test_format_missing_field_error(self):
        """Test formatting of missing field error"""
        schemas = [BodyFieldSchema(name="name", type="string", required=True)]
        model = build_pydantic_model(schemas)
        
        body = {}
        try:
            model(**body)
        except ValidationError as e:
            errors = format_validation_errors(e, body)
            assert len(errors) > 0
            error = errors[0]
            assert "body.name" in error["field"]
            assert "required" in error["error"] or "missing" in error["error"]
    
    def test_format_type_error(self):
        """Test formatting of type mismatch error"""
        schemas = [BodyFieldSchema(name="age", type="number", required=True)]
        model = build_pydantic_model(schemas)
        
        body = {"age": "not a number"}
        try:
            model(**body)
        except ValidationError as e:
            errors = format_validation_errors(e, body)
            assert len(errors) > 0
            error = errors[0]
            assert "body.age" in error["field"]
            assert "received" in error
            assert error["received"] == "not a number"
    
    def test_format_includes_received_value(self):
        """Test that errors include received value"""
        schemas = [BodyFieldSchema(name="count", type="number", min=1, max=10, required=True)]
        model = build_pydantic_model(schemas)
        
        body = {"count": 100}
        try:
            model(**body)
        except ValidationError as e:
            errors = format_validation_errors(e, body)
            assert len(errors) > 0
            error = errors[0]
            assert "received" in error
            assert error["received"] == 100
