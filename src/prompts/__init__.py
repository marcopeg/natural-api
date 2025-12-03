"""
Prompt-based routing system
"""
from src.prompts.loader import PromptMetadata, load_prompts
from src.prompts.variables import substitute_variables
from src.prompts.router import DynamicRouter, RouteMatch
from src.prompts.executor import PromptExecutor

__all__ = [
    "PromptMetadata",
    "load_prompts",
    "substitute_variables",
    "DynamicRouter",
    "RouteMatch",
    "PromptExecutor",
]
