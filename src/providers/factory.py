"""
Factory for creating AI providers
"""
from pathlib import Path
from src.providers.base import AIProvider
from src.providers.codex import CodexProvider


class ProviderNotFoundError(Exception):
    """Raised when requested provider is not found"""
    pass


class ProviderFactory:
    """Factory for creating AI provider instances"""
    
    # Registry of available providers
    _providers = {
        "codex": CodexProvider,
        # Future providers will be added here:
        # "claude": ClaudeProvider,
        # "copilot": CopilotProvider,
    }
    
    @classmethod
    def create(cls, provider_name: str, workspace_dir: Path, timeout: int = 60) -> AIProvider:
        """
        Create an AI provider instance
        
        Args:
            provider_name: Name of the provider (e.g., "codex", "claude")
            workspace_dir: Directory where AI can create/modify files
            timeout: Command timeout in seconds
            
        Returns:
            AIProvider instance
            
        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        provider_class = cls._providers.get(provider_name.lower())
        
        if provider_class is None:
            available = ", ".join(cls._providers.keys())
            raise ProviderNotFoundError(
                f"Provider '{provider_name}' not found. Available providers: {available}"
            )
        
        return provider_class(workspace_dir=workspace_dir, timeout=timeout)
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """Get list of available provider names"""
        return list(cls._providers.keys())
