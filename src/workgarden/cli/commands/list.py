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
        # Table output mode
        table = create_table("Managed Worktrees", ["Branch", "Path", "Ports", "Status"])

        for slug, wt in worktrees.items():
            status = manager.get_worktree_status(wt)

            # Format status with color
            if status == "OK":
                status_str = "[green]OK[/green]"
            elif status == "Missing":
                status_str = "[red]Missing[/red]"
            elif status == "Modified":
                status_str = "[yellow]Modified[/yellow]"
            else:
                status_str = status

            # Format ports
            if wt.port_mappings:
                ports_str = ", ".join(
                    f"{name}:{port}" for name, port in wt.port_mappings.items()
                )
            else:
                ports_str = "-"

            table.add_row(
                f"[cyan]{wt.branch}[/cyan]",
                str(wt.path),
                ports_str,
                status_str,
            )

        console.print(table)
