"""Rich console helpers."""

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


def print_error(message: str) -> None:
    """Print an error message."""
    error_console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def create_table(title: str, columns: list[str]) -> Table:
    """Create a styled table."""
    table = Table(title=title, show_header=True, header_style="bold")
    for col in columns:
        table.add_column(col)
    return table


def print_config_panel(config_dict: dict, title: str = "Configuration") -> None:
    """Print configuration as a formatted panel."""
    yaml_str = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title=title, border_style="blue"))


def print_operation_status(name: str, status: str) -> None:
    """Print operation status with appropriate styling.

    Args:
        name: Operation name/description
        status: One of "starting", "completed", "failed", "rolling_back", "skipped"
    """
    status_styles = {
        "starting": "[blue]...[/blue]",
        "completed": "[green]OK[/green]",
        "failed": "[red]FAILED[/red]",
        "rolling_back": "[yellow]ROLLBACK[/yellow]",
        "skipped": "[dim]SKIPPED[/dim]",
    }
    style = status_styles.get(status, status)
    console.print(f"  {style} {name}")


def print_dry_run_banner() -> None:
    """Print a banner indicating dry-run mode."""
    console.print(
        Panel(
            "[yellow]DRY RUN MODE[/yellow] - No changes will be made",
            border_style="yellow",
        )
    )
