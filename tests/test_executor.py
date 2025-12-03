"""
Unit tests for prompt executor module
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.prompts.executor import PromptExecutor
from src.prompts.loader import PromptMetadata
from src.providers.base import AIProviderResult


@pytest.fixture
def mock_provider():
    """Create a mock AI provider"""
    provider = Mock()
    provider.name = "mock"
    provider.is_available.return_value = True
    provider.execute.return_value = AIProviderResult(
        stdout="Mock output",
        stderr="",
        returncode=0,
        success=True,
        command="mock command"
    )
    return provider


@pytest.fixture
def executor():
    """Create a PromptExecutor"""
    return PromptExecutor(
        workspace_dir=Path("/tmp/test"),
        timeout=60
    )


@pytest.fixture
def sample_prompt():
    """Create a sample prompt metadata"""
    return PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model=None,
        agent=None,
        raw_content="Hello ${name}!",
        body_schema=None
    )


def test_execute_with_path_params(executor, sample_prompt, mock_provider):
    """Test prompt execution with path parameters"""
    with patch('src.prompts.executor.ProviderFactory.create', return_value=mock_provider):
        result = executor.execute(sample_prompt, route_params={"name": "Alice"})
        
        assert result.success
        assert result.stdout == "Mock output"
        
        # Verify provider was called with substituted prompt
        mock_provider.execute.assert_called_once()
        call_args = mock_provider.execute.call_args[0][0]
        assert call_args == "Hello Alice!"


def test_execute_with_model_override(executor, mock_provider):
    """Test execution with model override"""
    prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model="gpt-5.1-codex-mini",
        agent=None,
        raw_content="Test prompt",
        body_schema=None
    )
    
    with patch('src.prompts.executor.ProviderFactory.create', return_value=mock_provider):
        result = executor.execute(prompt, route_params={})
        
        # Verify model was passed to provider
        mock_provider.execute.assert_called_once_with("Test prompt", model="gpt-5.1-codex-mini", dry_run=False)


def test_execute_without_model_override(executor, sample_prompt, mock_provider):
    """Test execution without model override"""
    with patch('src.prompts.executor.ProviderFactory.create', return_value=mock_provider):
        result = executor.execute(sample_prompt, route_params={})
        
        # Verify execute called without model parameter
        mock_provider.execute.assert_called_once_with("Hello !", dry_run=False)


def test_execute_with_agent_override(executor, mock_provider):
    """Test execution with custom agent"""
    prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test",
        model=None,
        agent="custom-agent",
        raw_content="Test",
        body_schema=None
    )
    
    with patch('src.prompts.executor.ProviderFactory.create', return_value=mock_provider) as mock_create:
        executor.execute(prompt, route_params={})
        
        # Verify correct provider was requested
        mock_create.assert_called_once()
        assert mock_create.call_args[1]['provider_name'] == "custom-agent"


def test_execute_with_default_provider(executor, sample_prompt, mock_provider):
    """Test execution uses default provider when no agent specified"""
    with patch('src.prompts.executor.ProviderFactory.create', return_value=mock_provider) as mock_create:
        with patch('src.prompts.executor.config.AI_PROVIDER', 'codex'):
            executor.execute(sample_prompt, route_params={})
            
            # Verify default provider was used
            assert mock_create.call_args[1]['provider_name'] == 'codex'


def test_execute_variable_substitution(executor, mock_provider):
    """Test that variables are properly substituted"""
    prompt = PromptMetadata(
        filename="test",
        filepath=Path("/tmp/test.md"),
        method="GET",
        route="/test/{id}",
        model=None,
        agent=None,
        raw_content="User ${id} with role ${role:guest}",
        body_schema=None
    )
    
    with patch('src.prompts.executor.ProviderFactory.create', return_value=mock_provider):
        executor.execute(prompt, route_params={"id": "123"})
        
        # Verify substitution
        call_args = mock_provider.execute.call_args[0][0]
        assert call_args == "User 123 with role guest"
