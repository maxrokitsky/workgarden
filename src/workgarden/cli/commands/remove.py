"""Remove command placeholder."""

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def remove(
    branch: str = typer.Argument(..., help="Branch/worktree to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal"),
    keep_branch: bool = typer.Option(False, "--keep-branch", help="Keep the git branch"),
    no_hooks: bool = typer.Option(False, "--no-hooks", help="Skip hook execution"),
) -> None:
    """Remove a worktree."""
    # TODO: Implement in Phase 5
    typer.echo(f"Removing worktree: {branch}")
    typer.echo("Not implemented yet - coming in Phase 5")
