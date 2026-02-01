"""Rich console helpers."""

import yaml
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
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


def create_table(
    title: str,
    columns: list[str] | list[dict],
) -> Table:
    """Create a styled table.

    Args:
        title: Table title
        columns: List of column names (str) or dicts with column config
                 Dict keys: name, justify, style, no_wrap
    """
    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        box=ROUNDED,
        border_style="dim",
        title_style="bold cyan",
        padding=(0, 1),
    )
    for col in columns:
        if isinstance(col, dict):
            table.add_column(
                col["name"],
                justify=col.get("justify", "left"),
                style=col.get("style"),
                no_wrap=col.get("no_wrap", False),
            )
        else:
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


class OperationProgressReporter:
    """Reports operation progress with live spinner updates.

    Shows a spinner while operation is running, then replaces with final status.
    Results in one line per operation instead of two (starting + completed).
    """

    def __init__(self) -> None:
        self._status: Status | None = None

    def __call__(self, name: str, status: str) -> None:
        """Handle operation status update.

        Args:
            name: Operation name/description
            status: One of "starting", "completed", "failed", "rolling_back", "skipped"
        """
        if status == "starting":
            self._stop_spinner()
            self._status = console.status(f"  [blue]...[/blue] {name}", spinner="dots")
            self._status.start()
        elif status == "skipped":
            self._stop_spinner()
            console.print(f"  [dim]SKIPPED[/dim] {name}")
        elif status == "completed":
            self._stop_spinner()
            console.print(f"  [green]OK[/green] {name}")
        elif status == "failed":
            self._stop_spinner()
            console.print(f"  [red]FAILED[/red] {name}")
        elif status == "rolling_back":
            self._stop_spinner()
            console.print(f"  [yellow]ROLLBACK[/yellow] {name}")
        else:
            raise ValueError(f"Unknown operation status: {status!r}")

    def _stop_spinner(self) -> None:
        """Stop the spinner if it's running."""
        if self._status:
            self._status.stop()
            self._status = None
