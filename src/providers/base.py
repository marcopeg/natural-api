"""
Abstract base class for AI providers
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path


class AIProviderResult:
    """Result from AI provider execution"""
    
    def __init__(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        success: bool,
        command: str,
        error_message: str | None = None
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.success = success
        self.command = command
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "success": self.success,
            "command": self.command,
            "error_message": self.error_message,
        }


class AIProvider(ABC):
    """Abstract base class for AI CLI providers"""
    
    def __init__(self, workspace_dir: Path, timeout: int = 60):
        self.workspace_dir = workspace_dir
        self.timeout = timeout
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider CLI is available"""
        pass
    
    @abstractmethod
    def execute(self, prompt: str, model: str | None = None, dry_run: bool = False) -> AIProviderResult:
        """
        Execute a prompt with the AI provider
        
        Args:
            prompt: The instruction/prompt to execute
            model: Optional model override (provider-specific)
            dry_run: If True, return command string without executing
            
        Returns:
            AIProviderResult with execution details
        """
        pass
