"""List command placeholder."""

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def list_worktrees(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all managed worktrees."""
    # TODO: Implement in Phase 5
    typer.echo("Listing worktrees...")
    typer.echo("Not implemented yet - coming in Phase 5")
