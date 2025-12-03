# Goal

Update GitHub Copilot project guidance to reflect current project resolution and agents composition behavior.

# Task

- Document that project resolution uses `data/projects/<project>`.
- Document that `AGENTS.md` is read directly from the project directory and composed with the prompt body:
  - If `{{PROMPT}}` placeholder exists in `AGENTS.md`, the prompt body is inserted at the placeholder.
  - Otherwise, agents content is concatenated with the prompt body.
- Clarify that variable substitution occurs after composition across the entire composed text.
- Clarify that no symlink is required or created for `AGENTS.md` in user workspaces.

# Where to Update

- File: `.github/copilot-instructions.md`
  - Add or amend a section describing project resolution and agents composition.
  - Remove any references to `AGENTS.md` symlink usage.

# Acceptance Criteria

- `.github/copilot-instructions.md` clearly states:
  - Project structure location: `data/projects/<project>`
  - `AGENTS.md` composition rules (placeholder vs concatenation)
  - Variable substitution after composition
  - No symlink requirement
- Instructions align with current implementation and `tasks/task012.md`.
