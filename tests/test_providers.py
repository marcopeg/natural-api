"""
Tests for AI providers
"""
import pytest
from pathlib import Path
from src.providers.base import AIProvider, AIProviderResult
from src.providers.codex import CodexProvider
from src.providers.factory import ProviderFactory, ProviderNotFoundError


class TestAIProviderResult:
    """Test AIProviderResult class"""
    
    def test_result_creation_success(self):
        """Test creating a successful result"""
        result = AIProviderResult(
            stdout="output",
            stderr="",
            returncode=0,
            success=True,
            command="test command",
            error_message=None
        )
        assert result.success is True
        assert result.stdout == "output"
        assert result.returncode == 0
    
    def test_result_creation_failure(self):
        """Test creating a failed result"""
        result = AIProviderResult(
            stdout="",
            stderr="error",
            returncode=1,
            success=False,
            command="failed command",
            error_message="Command failed"
        )
        assert result.success is False
        assert result.error_message == "Command failed"
    
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = AIProviderResult(
            stdout="out",
            stderr="err",
            returncode=0,
            success=True,
            command="dict command"
        )
        data = result.to_dict()
        assert data["stdout"] == "out"
        assert data["stderr"] == "err"
        assert data["returncode"] == 0
        assert data["success"] is True


class TestCodexProvider:
    """Test CodexProvider class"""
    
    def test_provider_name(self, tmp_path):
        """Test provider name property"""
        provider = CodexProvider(workspace_dir=tmp_path)
        assert provider.name == "codex"
    
    def test_provider_availability(self, tmp_path):
        """Test checking if codex is available"""
        provider = CodexProvider(workspace_dir=tmp_path)
        # This will return True or False depending on system
        result = provider.is_available()
        assert isinstance(result, bool)
    
    def test_execute_when_not_available(self, tmp_path, monkeypatch):
        """Test execution when codex is not available"""
        # Mock shutil.which to return None
        import shutil
        monkeypatch.setattr(shutil, "which", lambda x: None)
        
        provider = CodexProvider(workspace_dir=tmp_path)
        result = provider.execute("test prompt")
        
        assert result.success is False
        assert result.returncode == -1
        assert "not found" in result.stderr.lower()


class TestProviderFactory:
    """Test ProviderFactory class"""
    
    def test_create_codex_provider(self, tmp_path):
        """Test creating a codex provider"""
        provider = ProviderFactory.create("codex", workspace_dir=tmp_path)
        assert isinstance(provider, CodexProvider)
        assert provider.name == "codex"
    
    def test_create_unknown_provider(self, tmp_path):
        """Test creating an unknown provider raises error"""
        with pytest.raises(ProviderNotFoundError) as exc_info:
            ProviderFactory.create("unknown", workspace_dir=tmp_path)
        
        assert "unknown" in str(exc_info.value).lower()
        assert "available providers" in str(exc_info.value).lower()
    
    def test_list_providers(self):
        """Test listing available providers"""
        providers = ProviderFactory.list_providers()
        assert isinstance(providers, list)
        assert "codex" in providers
    
    def test_create_with_custom_timeout(self, tmp_path):
        """Test creating provider with custom timeout"""
        provider = ProviderFactory.create("codex", workspace_dir=tmp_path, timeout=120)
        assert provider.timeout == 120


class TestCodexProviderDryRun:
    """Tests for CodexProvider dry-run functionality"""
    
    def test_dry_run_returns_command_string(self, tmp_path):
        """Dry-run returns command without execution"""
        provider = CodexProvider(workspace_dir=tmp_path, timeout=60)
        result = provider.execute("Test prompt", dry_run=True)
        
        assert result.success is True
        assert result.returncode == 0
        assert result.stderr == ""
        assert "codex exec" in result.stdout
        assert "Test prompt" in result.stdout
        assert "--sandbox workspace-write" in result.stdout
    
    def test_dry_run_with_model_override(self, tmp_path):
        """Dry-run includes model in command"""
        provider = CodexProvider(workspace_dir=tmp_path, timeout=60)
        result = provider.execute("Test prompt", model="gpt-5.1-codex", dry_run=True)
        
        assert result.success is True
        assert "--model gpt-5.1-codex" in result.stdout
        assert "Test prompt" in result.stdout
    
    def test_dry_run_with_default_model(self, tmp_path):
        """Dry-run uses default model when not specified"""
        provider = CodexProvider(workspace_dir=tmp_path, timeout=60)
        result = provider.execute("Test prompt", dry_run=True)
        
        assert result.success is True
        assert "--model gpt-5.1-codex-mini" in result.stdout
    
    def test_dry_run_success_indicators(self, tmp_path):
        """Dry-run returns success=True, returncode=0, stderr empty"""
        provider = CodexProvider(workspace_dir=tmp_path, timeout=60)
        result = provider.execute("Any prompt", dry_run=True)
        
        assert result.success is True
        assert result.returncode == 0
        assert result.stderr == ""
        assert result.error_message is None

