"""
Unit tests for variable substitution module
"""
import pytest
from src.prompts.variables import substitute_variables


# Legacy syntax tests (deprecated but still supported)
def test_simple_substitution():
    """Test simple variable substitution (legacy syntax)"""
    template = "Hello ${name}!"
    result = substitute_variables(template, route_params={"name": "Alice"})
    assert result == "Hello Alice!"


def test_substitution_with_default():
    """Test variable with default value (legacy syntax)"""
    template = "Role: ${role:guest}"
    result = substitute_variables(template, route_params={})
    assert result == "Role: guest"


def test_missing_variable_no_default():
    """Test missing variable without default (should be empty string)"""
    template = "Hello ${name}!"
    result = substitute_variables(template, route_params={})
    assert result == "Hello !"


def test_missing_variable_with_default():
    """Test missing variable uses default value"""
    template = "${greeting:Hi} ${name}"
    result = substitute_variables(template, route_params={"name": "Bob"})
    assert result == "Hi Bob"


def test_multiple_variables():
    """Test multiple variables in same string"""
    template = "User ${name} has role ${role:guest} in ${department}"
    result = substitute_variables(template, route_params={"name": "Alice", "department": "Engineering"})
    assert result == "User Alice has role guest in Engineering"


def test_no_variables():
    """Test string with no variables"""
    template = "Just plain text"
    result = substitute_variables(template, route_params={})
    assert result == "Just plain text"


def test_variable_override_default():
    """Test that provided variable overrides default"""
    template = "Role: ${role:guest}"
    result = substitute_variables(template, route_params={"role": "admin"})
    assert result == "Role: admin"


def test_default_with_special_chars():
    """Test default values with special characters"""
    template = "${message:Hello, World!}"
    result = substitute_variables(template, route_params={})
    assert result == "Hello, World!"


def test_empty_default():
    """Test empty default value"""
    template = "${name:}"
    result = substitute_variables(template, route_params={})
    assert result == ""


def test_multiple_same_variable():
    """Test same variable used multiple times"""
    template = "${name} loves ${name}!"
    result = substitute_variables(template, route_params={"name": "Python"})
    assert result == "Python loves Python!"


def test_variable_names_with_underscores_and_numbers():
    """Test variable names with underscores and numbers"""
    template = "${var_1} ${var_2} ${_var3}"
    result = substitute_variables(template, route_params={"var_1": "A", "var_2": "B", "_var3": "C"})
    assert result == "A B C"


# New namespaced syntax tests
def test_route_namespace():
    """Test route.variable syntax"""
    template = "Hello ${route.name}!"
    result = substitute_variables(template, route_params={"name": "Alice"})
    assert result == "Hello Alice!"


def test_body_namespace():
    """Test body.variable syntax"""
    template = "Do: ${body.task}"
    result = substitute_variables(template, body_params={"task": "code"})
    assert result == "Do: code"


def test_route_namespace_with_default():
    """Test route.variable:default syntax"""
    template = "User ${route.name:Anonymous}"
    result = substitute_variables(template, route_params={})
    assert result == "User Anonymous"


def test_body_namespace_with_default():
    """Test body.variable:default syntax"""
    template = "Tone: ${body.tone:neutral}"
    result = substitute_variables(template, body_params={})
    assert result == "Tone: neutral"


def test_mixed_route_and_body():
    """Test mixing route and body variables"""
    template = "User ${route.name} wants ${body.action}"
    result = substitute_variables(
        template,
        route_params={"name": "Alice"},
        body_params={"action": "code"}
    )
    assert result == "User Alice wants code"


def test_body_variable_converted_to_string():
    """Test that body variables are converted to strings"""
    template = "Count: ${body.count}"
    result = substitute_variables(template, body_params={"count": 42})
    assert result == "Count: 42"


def test_route_missing_body_present():
    """Test route variable missing but body variable present"""
    template = "${route.name} ${body.task}"
    result = substitute_variables(
        template,
        route_params={},
        body_params={"task": "test"}
    )
    assert result == " test"


def test_all_namespaces_with_defaults():
    """Test complex template with all features"""
    template = "User ${route.name:Guest} wants to ${body.action:browse} with tone ${body.tone:casual}"
    result = substitute_variables(
        template,
        route_params={"name": "Alice"},
        body_params={"action": "code"}
    )
    assert result == "User Alice wants to code with tone casual"

