"""Remove command for worktree management."""

import typer

from workgarden.config.loader import ConfigLoader
from workgarden.core.worktree import RemoveOptions, WorktreeManager
from workgarden.exceptions import ConfigNotFoundError, RootDetectionError
from workgarden.utils.console import (
    OperationProgressReporter,
    console,
    print_error,
    print_success,
    print_warning,
)
from workgarden.utils.git import get_branch_slug

app = typer.Typer()


@app.callback(invoke_without_command=True)
def remove(
    branch: str = typer.Argument(..., help="Branch/worktree to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal"),
    keep_branch: bool = typer.Option(False, "--keep-branch", help="Keep the git branch"),
    no_hooks: bool = typer.Option(False, "--no-hooks", help="Skip hook execution"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Remove a worktree."""
    # Verify config exists
    try:
        config_loader = ConfigLoader()
        config_loader.load()
    except RootDetectionError:
        print_error("Not in a git repository")
        raise typer.Exit(1)
    except ConfigNotFoundError:
        print_error("No .workgarden.yaml found in main repository. Run 'wg config init' first.")
        raise typer.Exit(1)

    # Create manager
    manager = WorktreeManager()

    # Find worktree
    slug = get_branch_slug(branch)
    worktree = manager.state.get_worktree(slug)

    if not worktree:
        # Try to find by exact branch match
        for s, wt in manager.list().items():
            if wt.branch == branch:
                slug = s
                worktree = wt
                break

    if not worktree:
        print_error(f"Worktree not found for branch '{branch}'")
        raise typer.Exit(1)

    # Show worktree details
    console.print(f"Branch: [cyan]{worktree.branch}[/cyan]")
    console.print(f"Path: {worktree.path}")

    # Check status
    status = manager.get_worktree_status(worktree)
    if status == "Missing":
        print_warning("Worktree directory does not exist")
    elif status == "Modified":
        if force:
            print_warning("Worktree has uncommitted changes (will be removed with --force)")
        else:
            print_error("Worktree has uncommitted changes. Use --force to remove anyway.")
            raise typer.Exit(1)

    # Confirmation prompt
    if not yes:
        console.print()
        confirmed = typer.confirm("Remove this worktree?")
        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(0)

    # Set up progress callback
    manager.progress_callback = OperationProgressReporter()

    # Build options
    options = RemoveOptions(
        branch=branch,
        force=force,
        keep_branch=keep_branch,
        skip_hooks=no_hooks,
    )

    # Execute
    console.print()
    result = manager.remove(options)

    if result.success:
        print_success(f"Worktree removed: {worktree.branch}")
    else:
        print_error(result.error)
        raise typer.Exit(1)
