"""Create command for worktree management."""

import typer

from workgarden.config.loader import ConfigLoader
from workgarden.core.worktree import CreateOptions, WorktreeManager
from workgarden.exceptions import ConfigNotFoundError, EditorError, RootDetectionError
from workgarden.utils.console import (
    console,
    print_dry_run_banner,
    print_error,
    print_operation_status,
    print_success,
    print_warning,
)
from workgarden.utils.editor import get_default_editor, open_editor

app = typer.Typer()


@app.callback(invoke_without_command=True)
def create(
    branch: str = typer.Argument(..., help="Branch name for the worktree"),
    base: str | None = typer.Option(None, "--base", "-b", help="Base branch for new branch"),
    no_env: bool = typer.Option(False, "--no-env", help="Skip .env copying"),
    no_ports: bool = typer.Option(False, "--no-ports", help="Skip port allocation"),
    no_hooks: bool = typer.Option(False, "--no-hooks", help="Skip hook execution"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
    open_editor_flag: bool = typer.Option(False, "--open", "-o", help="Open worktree in editor"),
    no_open: bool = typer.Option(False, "--no-open", help="Skip editor (overrides auto_open)"),
) -> None:
    """Create a new worktree."""
    # Verify config exists
    try:
        config_loader = ConfigLoader()
        config = config_loader.load()
    except RootDetectionError:
        print_error("Not in a git repository")
        raise typer.Exit(1)
    except ConfigNotFoundError:
        print_error("No .workgarden.yaml found in main repository. Run 'wg config init' first.")
        raise typer.Exit(1)

    # Show dry-run banner if applicable
    if dry_run:
        print_dry_run_banner()

    # Create manager with progress callback
    def progress_callback(name: str, status: str) -> None:
        print_operation_status(name, status)

    manager = WorktreeManager(progress_callback=progress_callback)

    # Build options
    options = CreateOptions(
        branch=branch,
        base_branch=base,
        skip_env=no_env,
        skip_ports=no_ports,
        skip_hooks=no_hooks,
        dry_run=dry_run,
    )

    # Execute
    console.print(f"Creating worktree for branch: [cyan]{branch}[/cyan]")
    result = manager.create(options)

    if result.success:
        if dry_run:
            console.print("\n[yellow]Dry run complete - no changes made[/yellow]")
        else:
            print_success(f"Worktree created at: {result.worktree.path}")

            # Handle editor opening (post-transaction action)
            should_open = (open_editor_flag or config.editor.auto_open) and not no_open
            if should_open and not dry_run:
                editor_cmd = get_default_editor(config.editor.command)
                if editor_cmd:
                    try:
                        open_editor(result.worktree.path, editor_cmd)
                        console.print(
                            f"Opening in [green]{editor_cmd}[/green]"
                        )
                    except EditorError as e:
                        print_warning(f"Could not open editor: {e}")
                else:
                    print_warning(
                        "No editor available. Set editor.command in .workgarden.yaml "
                        "or $VISUAL/$EDITOR environment variable."
                    )
    else:
        print_error(result.error)
        if result.rolled_back:
            console.print("[yellow]Changes have been rolled back[/yellow]")
            if result.rollback_errors:
                console.print("[red]Rollback errors:[/red]")
                for err in result.rollback_errors:
                    console.print(f"  - {err}")
        raise typer.Exit(1)
