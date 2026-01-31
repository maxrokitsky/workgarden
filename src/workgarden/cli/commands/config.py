"""Config commands: init, show."""

from pathlib import Path

import typer

from workgarden.config.loader import ConfigLoader
from workgarden.config.schema import DEFAULT_CONFIG
from workgarden.exceptions import ConfigNotFoundError
from workgarden.utils.console import console, print_config_panel, print_error, print_success

app = typer.Typer(help="Configuration management.")


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Create a new .workgarden.yaml configuration file."""
    loader = ConfigLoader(Path.cwd())

    if loader.exists() and not force:
        print_error(f"Config file already exists: {loader.config_path}")
        print_error("Use --force to overwrite.")
        raise typer.Exit(1)

    loader.save(DEFAULT_CONFIG)
    print_success(f"Created {loader.config_path}")
    console.print("\nEdit this file to customize your worktree settings.")


@app.command()
def show() -> None:
    """Show current configuration."""
    loader = ConfigLoader(Path.cwd())

    try:
        config = loader.load()
    except ConfigNotFoundError:
        print_error(f"Config file not found: {loader.config_path}")
        print_error("Run 'wg config init' to create one.")
        raise typer.Exit(1)

    print_config_panel(config.to_yaml_dict())
