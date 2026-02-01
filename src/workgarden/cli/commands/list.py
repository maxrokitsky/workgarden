"""List command for worktree management."""

import json

import typer

from workgarden.config.loader import ConfigLoader
from workgarden.core.worktree import WorktreeManager
from workgarden.exceptions import ConfigNotFoundError, RootDetectionError
from workgarden.utils.console import console, create_table, print_error, print_info

app = typer.Typer()


@app.callback(invoke_without_command=True)
def list_worktrees(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all managed worktrees."""
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

    # Create manager and list worktrees
    manager = WorktreeManager()
    worktrees = manager.list()

    if not worktrees:
        if json_output:
            print("{}")
        else:
            print_info("No worktrees found")
        return

    if json_output:
        # JSON output mode - use print() to avoid Rich wrapping
        output = {}
        for slug, wt in worktrees.items():
            status = manager.get_worktree_status(wt)
            data = wt.model_dump_json_compatible()
            data["status"] = status
            output[slug] = data
        print(json.dumps(output, indent=2))
    else:
        # Table output mode with styled columns
        columns = [
            {"name": "Branch", "style": "cyan", "no_wrap": True},
            {"name": "Path", "style": "dim"},
            {"name": "Ports", "justify": "center"},
            {"name": "Status", "justify": "center", "no_wrap": True},
        ]
        table = create_table("Managed Worktrees", columns)

        for _slug, wt in worktrees.items():
            status = manager.get_worktree_status(wt)

            # Format status with color and icon
            status_styles = {
                "OK": "[green]● OK[/green]",
                "Missing": "[red]✗ Missing[/red]",
                "Modified": "[yellow]◐ Modified[/yellow]",
            }
            status_str = status_styles.get(status, status)

            # Format ports
            if wt.port_mappings:
                ports_str = ", ".join(
                    f"{name}:[bold]{port}[/bold]" for name, port in wt.port_mappings.items()
                )
            else:
                ports_str = "[dim]—[/dim]"

            table.add_row(
                wt.branch,
                str(wt.path),
                ports_str,
                status_str,
            )

        console.print(table)
