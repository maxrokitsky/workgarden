"""Open command for worktree management."""

import typer

from workgarden.config.loader import ConfigLoader
from workgarden.core.worktree import WorktreeManager
from workgarden.exceptions import ConfigNotFoundError, EditorError, RootDetectionError
from workgarden.utils.console import console, print_error, print_info, print_warning
from workgarden.utils.editor import (
    detect_available_editors,
    get_default_editor,
    open_editor,
)


def open_worktree(
    branch: str = typer.Argument(None, help="Branch name or slug to open"),
    editor: str | None = typer.Option(
        None, "--editor", "-e", help="Editor command to use (e.g., code, cursor)"
    ),
    list_editors: bool = typer.Option(
        False, "--list-editors", help="List available editors and exit"
    ),
) -> None:
    """Open a worktree in an editor."""
    # Handle --list-editors flag
    if list_editors:
        _show_available_editors()
        return

    # Branch is required if not listing editors
    if branch is None:
        print_error("Branch argument is required. Use --list-editors to see available editors.")
        raise typer.Exit(1)

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

    # Find worktree
    manager = WorktreeManager()
    result = manager._find_worktree_by_branch(branch)
    if not result:
        print_error(f"Worktree not found for branch '{branch}'")
        raise typer.Exit(1)

    slug, worktree = result

    # Check if worktree path exists
    if not worktree.path.exists():
        print_error(f"Worktree path does not exist: {worktree.path}")
        raise typer.Exit(1)

    # Determine editor to use
    editor_cmd = editor or get_default_editor(config.editor.command)

    if not editor_cmd:
        print_error(
            "No editor available. Set editor.command in .workgarden.yaml, "
            "$VISUAL, or $EDITOR environment variable."
        )
        print_info("Run 'wg open --list-editors' to see available editors.")
        raise typer.Exit(1)

    # Open editor
    try:
        open_editor(worktree.path, editor_cmd)
        console.print(f"Opening [cyan]{worktree.path}[/cyan] in [green]{editor_cmd}[/green]")
    except EditorError as e:
        print_warning(str(e))
        raise typer.Exit(1)


def _show_available_editors() -> None:
    """Display available editors and configuration help."""
    editors = detect_available_editors()

    console.print("\n[bold]Available Editors:[/bold]\n")

    available = [e for e in editors if e.available]
    unavailable = [e for e in editors if not e.available]

    if available:
        for e in available:
            console.print(f"  [green]✓[/green] {e.name} ([cyan]{e.command}[/cyan])")
    else:
        console.print("  [yellow]No known editors detected[/yellow]")

    if unavailable:
        console.print("\n[dim]Not installed:[/dim]")
        for e in unavailable:
            console.print(f"  [dim]✗ {e.name} ({e.command})[/dim]")

    console.print("\n[bold]Configuration:[/bold]")
    console.print("  Set default editor in .workgarden.yaml:")
    console.print("  [dim]editor:[/dim]")
    console.print("  [dim]  command: code  # or cursor, zed, etc.[/dim]")
    console.print("  [dim]  auto_open: true  # open automatically on create[/dim]")
    console.print("\n  Or set $VISUAL or $EDITOR environment variable.\n")
