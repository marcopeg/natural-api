# Goal

Improve the composition of the command that is provided to the AI Agent by integrating project-level agents instructions and then applying variable substitution once over the fully composed text.

# Context

- Project resolution: `data/projects/<project>` (via configuration/resolution in code).
- Agents file: Optional project-level `AGENTS.md` located at `data/projects/<project>/AGENTS.md`.

# Task

Implement prompt composition with these rules:

1. Locate the project's `AGENTS.md` at `data/projects/<project>/AGENTS.md`.
2. If `AGENTS.md` exists:
	- If it contains the placeholder `{{PROMPT}}`, insert the prompt body at that placeholder (replace occurrences of `{{PROMPT}}`).
	- Otherwise, compose by concatenating agents content followed by the prompt body.
3. If `AGENTS.md` does not exist, use the prompt body as-is.
4. Perform variable substitution after composition, over the entire composed text. Substitution supports `${variable}` and `${variable:default}` with values sourced from route parameters and validated body parameters.
5. Do not introduce any caching; read `AGENTS.md` on each request.

# Non-Goals

- Performance optimizations, security hardening, and scalability concerns are out of scope for this task.

# Cleanup

- The legacy symlink behavior for `AGENTS.md` is now unnecessary because composition reads the project `AGENTS.md` directly. Identify and remove the symlink creation/update logic from the codebase so that user workspaces no longer contain (or rely on) an `AGENTS.md` symlink. The current logic lives in `src/main.py` within `setup_user_workspace`.

# Acceptance Criteria

- Placeholder composition: When `AGENTS.md` contains `{{PROMPT}}`, the prompt body is inserted at the placeholder location, and variable substitution is applied over the resulting text.
- Concatenation composition: When `AGENTS.md` has no `{{PROMPT}}`, the final text is the agents content followed by the prompt body; variable substitution is applied over the resulting text.
- Missing `AGENTS.md`: If the file is not present, the final text equals the prompt body; variable substitution is applied.
- Substitution scope: Variable substitution applies to the entire composed text (agents + prompt) with default values honored and missing values without defaults replaced with empty strings.
- No caching: Changes to `AGENTS.md` are reflected on the very next request without restart.
- Symlink removal: `setup_user_workspace` (and any other places) no longer create or update an `AGENTS.md` symlink.

# Notes

- Keep the composition logic isolated (e.g., in a dedicated utility/module) because it will evolve.

# Follow-up Task

- Create a task to update the GitHub Copilot project guidance to clearly state that project resolution uses `data/projects/<project>` and that `AGENTS.md` is read directly (no symlink requirement).