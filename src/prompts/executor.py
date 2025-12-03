"""
Prompt executor module - executes prompts with AI provider
"""
import logging
from pathlib import Path

from src.prompts.loader import PromptMetadata
from src.prompts.variables import substitute_variables
from src.providers.factory import ProviderFactory
from src.providers.base import AIProviderResult
from src.config import config


logger = logging.getLogger(__name__)


class PromptExecutor:
    """Executes prompts using AI provider"""
    
    def __init__(self, workspace_dir: Path, timeout: int):
        """
        Initialize executor.
        
        Args:
            workspace_dir: Workspace directory for AI operations
            timeout: Command timeout in seconds
        """
        self.workspace_dir = workspace_dir
        self.timeout = timeout
    
    def execute(
        self,
        prompt: PromptMetadata,
        route_params: dict[str, str] | None = None,
        body_params: dict[str, str] | None = None,
        dry_run: bool = False,
    ) -> AIProviderResult:
        """
        Execute a prompt with variable substitution.
        
        Args:
            prompt: Prompt metadata to execute
            route_params: Route path parameters for variable substitution
            body_params: Request body fields for variable substitution
            dry_run: If True, return command string without executing
            
        Returns:
            AIProviderResult from provider execution
        """
        # Substitute variables in prompt body
        processed_prompt = substitute_variables(
            prompt.raw_content,
            route_params=route_params,
            body_params=body_params
        )
        logger.debug(f"Processed prompt: {processed_prompt[:100]}...")
        
        # Determine which provider to use
        provider_name = prompt.agent if prompt.agent else config.AI_PROVIDER
        
        # Create provider
        provider = ProviderFactory.create(
            provider_name=provider_name,
            workspace_dir=self.workspace_dir,
            timeout=self.timeout
        )
        
        logger.info(f"Executing prompt '{prompt.filename}' with provider '{provider.name}'")
        
        # Execute with model override if specified
        if prompt.model:
            logger.info(f"Using model override: {prompt.model}")
            result = provider.execute(processed_prompt, model=prompt.model, dry_run=dry_run)
        else:
            result = provider.execute(processed_prompt, dry_run=dry_run)
        
        logger.debug(f"Execution result: success={result.success}, returncode={result.returncode}")
        
        return result
