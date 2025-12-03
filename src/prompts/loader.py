"""
Prompt loader module - loads and parses prompt files with YAML frontmatter
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import frontmatter


logger = logging.getLogger(__name__)


@dataclass
class PromptMetadata:
    """Metadata for a prompt file"""
    filename: str  # without .md extension
    filepath: Path  # full path to file
    method: str  # HTTP method (default "GET")
    route: str | None  # explicit route or None for fallback
    model: str | None  # model override
    agent: str | None  # provider override
    raw_content: str  # prompt body after frontmatter
    body_schema: dict[str, Any] | None = None  # body validation schema
    dry: bool | None = None  # dry-run mode override


def load_prompts(prompts_dir: Path) -> list[PromptMetadata]:
    """
    Load all prompt files from directory and parse their frontmatter.
    
    Args:
        prompts_dir: Directory containing *.md prompt files
        
    Returns:
        List of PromptMetadata objects
    """
    prompts: list[PromptMetadata] = []
    
    if not prompts_dir.exists():
        logger.warning(f"Prompts directory does not exist: {prompts_dir}")
        return prompts
    
    if not prompts_dir.is_dir():
        logger.warning(f"Prompts path is not a directory: {prompts_dir}")
        return prompts
    
    # Scan for .md files
    md_files = sorted(prompts_dir.glob("*.md"))
    
    if not md_files:
        logger.info(f"No prompt files found in {prompts_dir}")
        return prompts
    
    for filepath in md_files:
        try:
            # Read and parse frontmatter
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Extract filename without extension
            filename = filepath.stem
            
            # Extract frontmatter fields with defaults
            metadata = post.metadata if isinstance(post.metadata, dict) else {}
            
            method = str(metadata.get('method', 'GET')).upper()
            route = metadata.get('route')
            if route is not None:
                route = str(route)
            
            model = metadata.get('model')
            if model is not None:
                model = str(model)
            
            agent = metadata.get('agent')
            if agent is not None:
                agent = str(agent)
            
            # Get dry-run mode if present
            dry = metadata.get('dry')
            if dry is not None:
                # Parse as boolean
                if isinstance(dry, bool):
                    pass  # Already boolean
                elif isinstance(dry, str):
                    dry = dry.lower() in ('true', '1', 'yes')
                else:
                    dry = bool(dry)
            
            # Get body schema if present
            body_schema = metadata.get('body')
            if body_schema is not None and not isinstance(body_schema, dict):
                logger.warning(f"Prompt {filename}: 'body' must be a dict, ignoring")
                body_schema = None
            
            # Get prompt body content
            raw_content = post.content.strip()
            
            prompt = PromptMetadata(
                filename=filename,
                filepath=filepath,
                method=method,
                route=route,
                model=model,
                agent=agent,
                raw_content=raw_content,
                body_schema=body_schema,
                dry=dry
            )
            
            prompts.append(prompt)
            logger.debug(f"Loaded prompt: {filename} (method={method}, route={route})")
            
        except Exception as e:
            logger.warning(f"Failed to load prompt file {filepath}: {e}")
            # Skip malformed files, continue with others
            continue
    
    logger.info(f"Loaded {len(prompts)} prompt(s) from {prompts_dir}")
    logger.debug(f"Prompts: {[p.filename for p in prompts]}")
    
    return prompts
