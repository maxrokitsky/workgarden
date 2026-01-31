# Workgarden

CLI tool for managing git worktrees with Docker Compose and Claude Code support.

## Installation

```bash
uv sync
```

## Usage

```bash
# Initialize configuration
wg config init

# Show configuration
wg config show

# Create a worktree (coming soon)
wg create feature/my-feature

# List worktrees (coming soon)
wg list

# Remove a worktree (coming soon)
wg remove feature/my-feature
```

## Configuration

Configuration is stored in `.workgarden.yaml`. Run `wg config init` to create a default configuration file.
