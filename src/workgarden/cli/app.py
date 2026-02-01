"""Main Typer application."""

import typer

from workgarden.cli.commands import config, create, remove
from workgarden.cli.commands import list as list_cmd
from workgarden.cli.commands import open as open_cmd

app = typer.Typer(
    name="workgarden",
    help="Git worktree manager with Docker Compose support.",
    no_args_is_help=True,
)

app.add_typer(config.app, name="config")
app.command(name="create")(create.create)
app.command(name="remove")(remove.remove)
app.command(name="list")(list_cmd.list_worktrees)
app.command(name="open")(open_cmd.open_worktree)


@app.callback()
def main() -> None:
    """Workgarden - Git worktree manager."""
    pass


if __name__ == "__main__":
    app()
