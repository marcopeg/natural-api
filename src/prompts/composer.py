"""
Prompt composition utilities: merge project-level AGENTS.md with prompt body.

Rules:
- Project is resolved under data/projects/<project> via Config.get_project_dir(project_id)
- If AGENTS.md exists:
  - If it contains a "{{PROMPT}}" placeholder, replace it with the prompt body
  - Else, concatenate as: agents + two newlines + prompt body
- If AGENTS.md is missing: use the prompt body as-is
- Variable substitution happens after composition (handled by executor)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.config import Config

logger = logging.getLogger(__name__)


def _read_agents_file(project_id: str) -> Optional[str]:
    """Read AGENTS.md content for a project if present."""
    agents_path: Path = Config.get_project_dir(project_id) / "AGENTS.md"
    try:
        if agents_path.exists() and agents_path.is_file():
            content = agents_path.read_text(encoding="utf-8")
            logger.debug(f"Loaded AGENTS.md for project '{project_id}' ({len(content)} bytes)")
            return content
        logger.debug(f"No AGENTS.md found for project '{project_id}'")
        return None
    except Exception as e:
        # Do not fail request if AGENTS.md cannot be read; just log and continue
        logger.warning(f"Failed to read AGENTS.md for project '{project_id}': {e}")
        return None


def compose_prompt(prompt_body: str, project_id: str) -> str:
    """
    Compose the final prompt by merging project AGENTS.md (if any) with the given prompt body.
    
    Args:
        prompt_body: The raw prompt body content from the prompt file
        project_id: The project identifier used to locate AGENTS.md
    
    Returns:
        The composed prompt text (agents + prompt) ready for variable substitution.
    """
    agents = _read_agents_file(project_id)
    if not agents:
        return prompt_body

    placeholder = "{{PROMPT}}"
    if placeholder in agents:
        # Replace first (and all) occurrences to allow flexible templates
        composed = agents.replace(placeholder, prompt_body)
    else:
        # Default concatenation: agents + blank line + prompt
        composed = f"{agents}\n\n{prompt_body}"

    logger.debug(f"Composed prompt length: {len(composed)} (project={project_id})")
    return composed
