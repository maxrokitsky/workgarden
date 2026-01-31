"""Create command placeholder."""

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def create(
    branch: str = typer.Argument(..., help="Branch name for the worktree"),
    base: str | None = typer.Option(None, "--base", "-b", help="Base branch for new branch"),
    no_env: bool = typer.Option(False, "--no-env", help="Skip .env copying"),
    no_ports: bool = typer.Option(False, "--no-ports", help="Skip port allocation"),
    no_hooks: bool = typer.Option(False, "--no-hooks", help="Skip hook execution"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Create a new worktree."""
    # TODO: Implement in Phase 5
    typer.echo(f"Creating worktree for branch: {branch}")
    typer.echo("Not implemented yet - coming in Phase 5")
