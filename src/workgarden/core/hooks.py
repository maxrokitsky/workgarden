"""Lifecycle hook execution for worktree operations."""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from workgarden.exceptions import HookError
from workgarden.utils.template import TemplateContext, substitute_variables

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # 5 minutes


@dataclass
class HookResult:
    """Result of a single hook execution."""

    command: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    error: str | None = None


@dataclass
class HookRunnerResult:
    """Result of all hooks for a lifecycle event."""

    hook_name: str
    success: bool
    results: list[HookResult] = field(default_factory=list)


class HookRunner:
    """Execute shell commands at worktree lifecycle points."""

    def __init__(
        self,
        context: TemplateContext,
        working_dir: Path | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """Initialize hook runner.

        Args:
            context: Template context for variable substitution
            working_dir: Directory to run commands in (defaults to context.worktree_path)
            timeout: Timeout in seconds for each command (default 5 minutes)
        """
        self.context = context
        self.working_dir = working_dir or context.worktree_path
        self.timeout = timeout

    def _build_environment(self) -> dict[str, str]:
        """Build environment with WG_* variables."""
        env = os.environ.copy()

        # Add WG_* prefixed variables
        for name, value in self.context.get_variables().items():
            env[f"WG_{name}"] = value

        return env

    def _execute_hook(self, command: str) -> HookResult:
        """Execute a single hook command.

        Args:
            command: The shell command to execute (with {{VAR}} placeholders)

        Returns:
            HookResult with execution details
        """
        # Substitute variables in command
        substituted_command = substitute_variables(command, self.context)

        logger.debug(f"Executing hook: {substituted_command}")

        try:
            result = subprocess.run(
                substituted_command,
                shell=True,
                cwd=self.working_dir,
                env=self._build_environment(),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            success = result.returncode == 0

            if not success:
                logger.warning(
                    f"Hook command failed with code {result.returncode}: {substituted_command}"
                )
                if result.stderr:
                    logger.warning(f"stderr: {result.stderr}")

            return HookResult(
                command=substituted_command,
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )

        except subprocess.TimeoutExpired as e:
            logger.error(f"Hook command timed out after {self.timeout}s: {substituted_command}")
            return HookResult(
                command=substituted_command,
                success=False,
                error=f"Command timed out after {self.timeout} seconds",
                stdout=e.stdout or "" if hasattr(e, "stdout") else "",
                stderr=e.stderr or "" if hasattr(e, "stderr") else "",
            )

        except Exception as e:
            logger.error(f"Hook command failed: {substituted_command}: {e}")
            return HookResult(
                command=substituted_command,
                success=False,
                error=str(e),
            )

    def run(self, hook_name: str, hooks: list[str]) -> HookRunnerResult:
        """Execute all hooks for a lifecycle event.

        Uses fail-fast behavior: stops on first failure.

        Args:
            hook_name: Name of the lifecycle event (e.g., "post_create")
            hooks: List of shell commands to execute

        Returns:
            HookRunnerResult with all execution results

        Raises:
            HookError: If any hook fails
        """
        if not hooks:
            logger.debug(f"No {hook_name} hooks to run")
            return HookRunnerResult(hook_name=hook_name, success=True)

        logger.info(f"Running {len(hooks)} {hook_name} hook(s)")

        results: list[HookResult] = []

        for command in hooks:
            result = self._execute_hook(command)
            results.append(result)

            if not result.success:
                # Fail-fast: stop on first failure
                error_msg = result.error or result.stderr or f"Exit code {result.return_code}"
                raise HookError(
                    f"{hook_name} hook failed: {result.command}\n{error_msg}"
                )

        logger.info(f"All {hook_name} hooks completed successfully")
        return HookRunnerResult(hook_name=hook_name, success=True, results=results)
