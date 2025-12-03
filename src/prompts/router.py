"""
Route matcher module - matches HTTP requests to prompt files
"""
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from src.prompts.loader import PromptMetadata, load_prompts


logger = logging.getLogger(__name__)


@dataclass
class RouteMatch:
    """Result of route matching"""
    prompt: PromptMetadata
    match_type: Literal["explicit", "fallback"]
    path_params: dict[str, str]


class DynamicRouter:
    """Dynamic router that matches requests to prompts"""
    
    def __init__(self, prompts_dir: Path):
        """
        Initialize router with prompts directory.
        
        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = prompts_dir
        self.prompts: list[PromptMetadata] = []
    
    def load_prompts(self) -> None:
        """Load all prompts from directory"""
        self.prompts = load_prompts(self.prompts_dir)
        logger.info(f"Router loaded {len(self.prompts)} prompt(s)")
    
    def match_route(self, method: str, path: str) -> RouteMatch | None:
        """
        Match HTTP request to a prompt.
        
        Priority:
        1. Explicit routes (prompts with 'route' config)
        2. Fallback filename routes (GET /{filename})
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path (must start with /)
            
        Returns:
            RouteMatch if matched, None otherwise
        """
        method = method.upper()
        
        # Try explicit route matching first
        match = self._match_explicit(method, path)
        if match:
            logger.info(f"Matched explicit route: {match.prompt.filename} ({method} {path})")
            return match
        
        # Try fallback filename matching
        match = self._match_fallback(method, path)
        if match:
            logger.info(f"Matched fallback route: {match.prompt.filename} ({method} {path})")
            return match
        
        logger.debug(f"No route match for {method} {path}")
        return None
    
    def _match_explicit(self, method: str, path: str) -> RouteMatch | None:
        """
        Match against prompts with explicit route configuration.
        
        Returns first match found.
        """
        for prompt in self.prompts:
            if prompt.route is None:
                continue
            
            # Check method matches
            if prompt.method != method:
                continue
            
            # Check path pattern matches
            path_params = self._extract_path_params(prompt.route, path)
            if path_params is not None:
                return RouteMatch(
                    prompt=prompt,
                    match_type="explicit",
                    path_params=path_params
                )
        
        return None
    
    def _match_fallback(self, method: str, path: str) -> RouteMatch | None:
        """
        Match against filename-based routes.
        
        Only matches GET requests to /{filename}
        """
        # Only GET requests for fallback
        if method != "GET":
            return None
        
        # Extract filename from path (remove leading slash)
        if not path.startswith("/"):
            return None
        
        filename = path[1:]  # Remove leading /
        
        # No slashes allowed in fallback (single segment only)
        if "/" in filename:
            return None
        
        # Find prompt with matching filename
        for prompt in self.prompts:
            if prompt.filename == filename:
                return RouteMatch(
                    prompt=prompt,
                    match_type="fallback",
                    path_params={}
                )
        
        return None
    
    def _extract_path_params(self, pattern: str, path: str) -> dict[str, str] | None:
        """
        Extract path parameters from URL path using FastAPI-style pattern.
        
        Supports:
        - {name} - matches single path segment
        - {path:path} - matches entire remaining path (including slashes)
        
        Args:
            pattern: Route pattern like "/user/{name}" or "/files/{path:path}"
            path: Actual request path like "/user/alice"
            
        Returns:
            Dictionary of extracted parameters, or None if no match
        """
        # Convert FastAPI-style pattern to regex
        regex_pattern = pattern
        
        # Find all {param} and {param:path} patterns
        param_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)(?::path)?\}')
        
        # Track parameter names and types
        params_info = []
        for match in param_pattern.finditer(pattern):
            param_name = match.group(1)
            is_path_type = ":path}" in match.group(0)
            params_info.append((param_name, is_path_type))
        
        # Replace {param} with named capture groups
        # {name} -> (?P<name>[^/]+) (match until next slash)
        # {path:path} -> (?P<path>.+) (match everything)
        regex_pattern = re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', r'(?P<\1>[^/]+)', regex_pattern)
        regex_pattern = re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_]*):path\}', r'(?P<\1>.+)', regex_pattern)
        
        # Escape special regex characters except our named groups
        # Add anchors for exact match
        regex_pattern = f'^{regex_pattern}$'
        
        try:
            match = re.match(regex_pattern, path)
            if match:
                return match.groupdict()
            return None
        except re.error as e:
            logger.warning(f"Invalid route pattern '{pattern}': {e}")
            return None
