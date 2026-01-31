"""Template variable substitution."""

import re
from pathlib import Path


class TemplateContext:
    """Context for template variable substitution."""

    def __init__(
        self,
        branch: str = "",
        branch_slug: str = "",
        worktree_path: Path | None = None,
        repo_name: str = "",
        port_mappings: dict[str, int] | None = None,
        custom_variables: dict[str, str] | None = None,
    ):
        self.branch = branch
        self.branch_slug = branch_slug
        self.worktree_path = worktree_path or Path.cwd()
        self.repo_name = repo_name
        self.port_mappings = port_mappings or {}
        self.custom_variables = custom_variables or {}

    def get_variables(self) -> dict[str, str]:
        """Get all available variables for substitution."""
        variables = {
            "BRANCH": self.branch,
            "BRANCH_SLUG": self.branch_slug,
            "WORKTREE_PATH": str(self.worktree_path),
            "REPO_NAME": self.repo_name,
        }

        # Add port variables (PORT_WEB, PORT_DB, etc.)
        for name, port in self.port_mappings.items():
            variables[f"PORT_{name.upper()}"] = str(port)

        # Add custom variables
        variables.update(self.custom_variables)

        return variables


def substitute_variables(text: str, context: TemplateContext) -> str:
    """Substitute {{VARIABLE}} placeholders in text."""
    variables = context.get_variables()

    def replace(match: re.Match) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    # Match {{VARIABLE}} pattern
    pattern = r"\{\{([A-Z_][A-Z0-9_]*)\}\}"
    return re.sub(pattern, replace, text)


def substitute_path_variables(path_template: str, context: TemplateContext) -> str:
    """Substitute {variable} placeholders in path templates."""
    variables = {
        "repo_name": context.repo_name,
        "branch": context.branch,
        "branch_slug": context.branch_slug,
    }

    def replace(match: re.Match) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    # Match {variable} pattern (lowercase)
    pattern = r"\{([a-z_]+)\}"
    return re.sub(pattern, replace, path_template)
