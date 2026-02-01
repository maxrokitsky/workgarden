"""Worktree management orchestration with transaction support."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from workgarden.config.loader import ConfigLoader
from workgarden.config.schema import WorkgardenConfig
from workgarden.core.hooks import HookRunner
from workgarden.exceptions import (
    GitError,
    HookError,
)
from workgarden.models.state import StateManager
from workgarden.models.worktree import WorktreeInfo
from workgarden.utils.git import GitUtils, get_branch_slug
from workgarden.utils.root import find_main_repo_root
from workgarden.utils.template import TemplateContext, substitute_path_variables


class OperationStatus(Enum):
    """Status of an operation in a transaction."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


@dataclass
class CreateOptions:
    """Options for creating a worktree."""

    branch: str
    base_branch: str | None = None
    skip_env: bool = False
    skip_ports: bool = False
    skip_hooks: bool = False
    dry_run: bool = False


@dataclass
class RemoveOptions:
    """Options for removing a worktree."""

    branch: str
    force: bool = False
    keep_branch: bool = False
    skip_hooks: bool = False


@dataclass
class OperationResult:
    """Result of a worktree operation."""

    success: bool
    worktree: WorktreeInfo | None = None
    error: str | None = None
    rolled_back: bool = False
    rollback_errors: list[str] = field(default_factory=list)


class Operation(ABC):
    """Abstract base class for transactional operations."""

    def __init__(self, name: str):
        self.name = name
        self.status = OperationStatus.PENDING

    @abstractmethod
    def execute(self) -> None:
        """Execute the operation."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the operation."""

    def can_rollback(self) -> bool:
        """Check if operation can be rolled back."""
        return True


class CreateWorktreeOperation(Operation):
    """Operation to create a git worktree."""

    def __init__(
        self,
        git: GitUtils,
        path: Path,
        branch: str,
        create_branch: bool = False,
    ):
        super().__init__(f"Create worktree at {path}")
        self.git = git
        self.path = path
        self.branch = branch
        self.create_branch = create_branch

    def execute(self) -> None:
        self.git.worktree_add(self.path, self.branch, create_branch=self.create_branch)

    def rollback(self) -> None:
        if self.path.exists():
            self.git.worktree_remove(self.path, force=True)


class UpdateStateOperation(Operation):
    """Operation to add worktree to state."""

    def __init__(self, state_manager: StateManager, slug: str, worktree: WorktreeInfo):
        super().__init__(f"Update state for {slug}")
        self.state_manager = state_manager
        self.slug = slug
        self.worktree = worktree

    def execute(self) -> None:
        self.state_manager.add_worktree(self.slug, self.worktree)

    def rollback(self) -> None:
        self.state_manager.remove_worktree(self.slug)


class RunHookOperation(Operation):
    """Operation to run lifecycle hooks."""

    def __init__(
        self,
        hook_name: str,
        hooks: list[str],
        context: TemplateContext,
        working_dir: Path | None = None,
    ):
        super().__init__(f"Run {hook_name} hooks")
        self.hook_name = hook_name
        self.hooks = hooks
        self.context = context
        self.working_dir = working_dir

    def execute(self) -> None:
        if not self.hooks:
            return

        runner = HookRunner(
            context=self.context,
            working_dir=self.working_dir,
        )
        runner.run(self.hook_name, self.hooks)

    def rollback(self) -> None:
        # Hooks cannot be rolled back - side effects can't be undone
        pass

    def can_rollback(self) -> bool:
        return False


ProgressCallback = Callable[[str, str], None]


class TransactionManager:
    """Manages a sequence of operations with rollback support."""

    def __init__(self, dry_run: bool = False, progress_callback: ProgressCallback | None = None):
        self.operations: list[Operation] = []
        self.dry_run = dry_run
        self.progress_callback = progress_callback
        self._completed: list[Operation] = []

    def add(self, operation: Operation) -> None:
        """Add an operation to the transaction."""
        self.operations.append(operation)

    def _report(self, name: str, status: str) -> None:
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(name, status)

    def execute(self) -> tuple[bool, str | None, list[str]]:
        """Execute all operations in order.

        Returns:
            Tuple of (success, error_message, rollback_errors)
        """
        self._completed = []
        rollback_errors: list[str] = []

        for op in self.operations:
            self._report(op.name, "starting")

            if self.dry_run:
                op.status = OperationStatus.SKIPPED
                self._report(op.name, "skipped")
                continue

            try:
                op.status = OperationStatus.IN_PROGRESS
                op.execute()
                op.status = OperationStatus.COMPLETED
                self._completed.append(op)
                self._report(op.name, "completed")
            except Exception as e:
                op.status = OperationStatus.FAILED
                self._report(op.name, "failed")
                error_msg = str(e)

                # Rollback completed operations in reverse order
                rollback_errors = self._rollback()
                return False, error_msg, rollback_errors

        return True, None, []

    def _rollback(self) -> list[str]:
        """Rollback completed operations in reverse order.

        Returns:
            List of rollback error messages
        """
        errors: list[str] = []

        for op in reversed(self._completed):
            if not op.can_rollback():
                continue

            self._report(op.name, "rolling_back")
            try:
                op.rollback()
                op.status = OperationStatus.ROLLED_BACK
            except Exception as e:
                errors.append(f"{op.name}: {e}")

        return errors


class WorktreeManager:
    """Main orchestrator for worktree operations."""

    def __init__(
        self,
        root_path: Path | None = None,
        progress_callback: ProgressCallback | None = None,
    ):
        self.root_path = root_path or find_main_repo_root()
        self.progress_callback = progress_callback
        self._git: GitUtils | None = None
        self._state: StateManager | None = None
        self._config_loader: ConfigLoader | None = None

    @property
    def git(self) -> GitUtils:
        """Lazy-load GitUtils."""
        if self._git is None:
            self._git = GitUtils(self.root_path)
        return self._git

    @property
    def state(self) -> StateManager:
        """Lazy-load StateManager."""
        if self._state is None:
            self._state = StateManager(self.root_path)
        return self._state

    @property
    def config_loader(self) -> ConfigLoader:
        """Lazy-load ConfigLoader."""
        if self._config_loader is None:
            self._config_loader = ConfigLoader(self.root_path)
        return self._config_loader

    @property
    def config(self) -> WorkgardenConfig:
        """Get loaded config."""
        return self.config_loader.config

    def _calculate_worktree_path(self, branch: str) -> Path:
        """Calculate the worktree path from config templates."""
        slug = get_branch_slug(branch)
        repo_name = self.git.get_repo_name()

        context = TemplateContext(
            branch=branch,
            branch_slug=slug,
            repo_name=repo_name,
        )

        # Resolve base path
        base_path = substitute_path_variables(self.config.worktree_base_path, context)
        # Resolve worktree naming
        worktree_name = substitute_path_variables(self.config.worktree_naming, context)

        # Combine paths - base_path is relative to root_path
        full_path = (self.root_path / base_path / worktree_name).resolve()
        return full_path

    def _find_worktree_by_branch(self, branch: str) -> tuple[str, WorktreeInfo] | None:
        """Find worktree by branch name or slug.

        Returns:
            Tuple of (slug, WorktreeInfo) or None if not found
        """
        slug = get_branch_slug(branch)
        worktree = self.state.get_worktree(slug)
        if worktree:
            return slug, worktree

        # Try to find by exact branch match
        for s, wt in self.state.list_worktrees().items():
            if wt.branch == branch:
                return s, wt

        return None

    def create(self, options: CreateOptions) -> OperationResult:
        """Create a new worktree.

        Args:
            options: CreateOptions with branch name and flags

        Returns:
            OperationResult with success status and worktree info
        """
        slug = get_branch_slug(options.branch)

        # Check if worktree already exists in state
        existing = self.state.get_worktree(slug)
        if existing:
            return OperationResult(
                success=False,
                error=f"Worktree already exists for branch '{options.branch}' at {existing.path}",
            )

        # Check if branch exists (determines if we need to create it)
        branch_exists = self.git.branch_exists(options.branch)
        create_branch = not branch_exists

        # Calculate worktree path
        worktree_path = self._calculate_worktree_path(options.branch)

        # Check if path already exists
        if worktree_path.exists() and not options.dry_run:
            return OperationResult(
                success=False,
                error=f"Path already exists: {worktree_path}",
            )

        # Build worktree info
        worktree_info = WorktreeInfo(
            path=worktree_path,
            branch=options.branch,
            port_mappings={},  # Empty for now - Phase 5 will add port allocation
        )

        # Build template context for hooks
        context = TemplateContext(
            branch=options.branch,
            branch_slug=slug,
            worktree_path=worktree_path,
            repo_name=self.git.get_repo_name(),
        )

        # Build transaction
        transaction = TransactionManager(
            dry_run=options.dry_run,
            progress_callback=self.progress_callback,
        )

        # Step 1: Create git worktree
        transaction.add(
            CreateWorktreeOperation(
                git=self.git,
                path=worktree_path,
                branch=options.branch,
                create_branch=create_branch,
            )
        )

        # Step 2: Run post_create hooks
        if not options.skip_hooks:
            transaction.add(
                RunHookOperation(
                    hook_name="post_create",
                    hooks=self.config.hooks.post_create,
                    context=context,
                    working_dir=worktree_path,
                )
            )

        # Step 3: Update state
        transaction.add(
            UpdateStateOperation(
                state_manager=self.state,
                slug=slug,
                worktree=worktree_info,
            )
        )

        # Step 4: Run post_setup hooks
        if not options.skip_hooks:
            transaction.add(
                RunHookOperation(
                    hook_name="post_setup",
                    hooks=self.config.hooks.post_setup,
                    context=context,
                    working_dir=worktree_path,
                )
            )

        # Execute transaction
        success, error, rollback_errors = transaction.execute()

        if success:
            return OperationResult(
                success=True,
                worktree=worktree_info,
            )
        else:
            return OperationResult(
                success=False,
                error=error,
                rolled_back=bool(rollback_errors) or len(transaction._completed) > 0,
                rollback_errors=rollback_errors,
            )

    def remove(self, options: RemoveOptions) -> OperationResult:
        """Remove an existing worktree.

        Args:
            options: RemoveOptions with branch name and flags

        Returns:
            OperationResult with success status
        """
        # Find worktree
        result = self._find_worktree_by_branch(options.branch)
        if not result:
            return OperationResult(
                success=False,
                error=f"Worktree not found for branch '{options.branch}'",
            )

        slug, worktree = result

        # Check for uncommitted changes (unless force)
        if worktree.path.exists() and not options.force:
            try:
                if self.git.has_uncommitted_changes(worktree.path):
                    return OperationResult(
                        success=False,
                        error="Worktree has uncommitted changes. Use --force to remove anyway.",
                    )
            except GitError:
                # Path might not be a valid git directory
                pass

        # Build template context for hooks
        context = TemplateContext(
            branch=worktree.branch,
            branch_slug=slug,
            worktree_path=worktree.path,
            repo_name=self.git.get_repo_name(),
            port_mappings=worktree.port_mappings,
        )

        # Run pre_remove hooks (run in worktree directory, fail if hooks fail)
        if not options.skip_hooks and self.config.hooks.pre_remove:
            if self.progress_callback:
                self.progress_callback("Run pre_remove hooks", "starting")
            try:
                runner = HookRunner(context=context, working_dir=worktree.path)
                runner.run("pre_remove", self.config.hooks.pre_remove)
                if self.progress_callback:
                    self.progress_callback("Run pre_remove hooks", "completed")
            except HookError as e:
                if self.progress_callback:
                    self.progress_callback("Run pre_remove hooks", "failed")
                return OperationResult(
                    success=False,
                    error=str(e),
                )

        # Remove git worktree
        if worktree.path.exists():
            if self.progress_callback:
                self.progress_callback(f"Remove worktree at {worktree.path}", "starting")
            try:
                self.git.worktree_remove(worktree.path, force=options.force)
                if self.progress_callback:
                    self.progress_callback(f"Remove worktree at {worktree.path}", "completed")
            except GitError as e:
                if self.progress_callback:
                    self.progress_callback(f"Remove worktree at {worktree.path}", "failed")
                return OperationResult(
                    success=False,
                    error=str(e),
                )

        # Remove from state
        if self.progress_callback:
            self.progress_callback(f"Update state for {slug}", "starting")
        self.state.remove_worktree(slug)
        if self.progress_callback:
            self.progress_callback(f"Update state for {slug}", "completed")

        # Delete branch (unless --keep-branch)
        if not options.keep_branch:
            if self.progress_callback:
                self.progress_callback(f"Delete branch {worktree.branch}", "starting")
            try:
                self.git.delete_branch(worktree.branch, force=options.force)
                if self.progress_callback:
                    self.progress_callback(f"Delete branch {worktree.branch}", "completed")
            except GitError:
                # Branch might not exist or be checked out elsewhere
                if self.progress_callback:
                    self.progress_callback(f"Delete branch {worktree.branch}", "skipped")

        # Run post_remove hooks (run in main repo directory, log warning but don't fail)
        if not options.skip_hooks and self.config.hooks.post_remove:
            if self.progress_callback:
                self.progress_callback("Run post_remove hooks", "starting")
            try:
                runner = HookRunner(context=context, working_dir=self.root_path)
                runner.run("post_remove", self.config.hooks.post_remove)
                if self.progress_callback:
                    self.progress_callback("Run post_remove hooks", "completed")
            except HookError as e:
                # Log warning but don't fail - worktree is already removed
                logging.getLogger(__name__).warning(f"post_remove hook failed: {e}")
                if self.progress_callback:
                    self.progress_callback("Run post_remove hooks", "warning")

        return OperationResult(
            success=True,
            worktree=worktree,
        )

    def list(self) -> dict[str, WorktreeInfo]:
        """List all managed worktrees.

        Returns:
            Dictionary mapping slug to WorktreeInfo
        """
        return self.state.list_worktrees()

    def get_worktree_status(self, worktree: WorktreeInfo) -> str:
        """Get status of a worktree.

        Returns:
            Status string: "OK", "Missing", or "Modified"
        """
        if not worktree.path.exists():
            return "Missing"

        try:
            if self.git.has_uncommitted_changes(worktree.path):
                return "Modified"
        except GitError:
            return "Missing"

        return "OK"
