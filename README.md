# Workgarden

CLI tool for managing git worktrees with automatic Docker Compose port allocation, environment file templating, and Claude Code configuration support.

!!! WORK IN PROGRESS

## Features

- **Worktree management** - Create, list, remove, and open git worktrees
- **Automatic port allocation** - Scans docker-compose for ports and allocates free ones per worktree
- **Environment templating** - Copy `.env` files with variable substitution (`{{BRANCH}}`, `{{PORT_*}}`, etc.)
- **Docker Compose override** - Generates `docker-compose.override.worktree.yml` without modifying originals
- **Editor integration** - Open worktrees in VS Code, Cursor, Zed, or any editor
- **Hooks** - Run custom scripts on `post_create` and `post_setup` events
- **Claude Code support** - Copies `.claude` configuration to worktrees

## Installation

```bash
uv sync  # TODO: replace with `uv tool`
```

## Usage

```bash
# Initialize configuration
wg config init

# Show configuration
wg config show

# Create a worktree
wg create feature/my-feature
wg create feature/my-feature --base main    # Create from specific base branch
wg create feature/my-feature --open         # Open in editor after creation
wg create feature/my-feature --dry-run      # Preview changes without executing

# List all managed worktrees
wg list
wg list --json                              # Output as JSON

# Open a worktree in editor
wg open feature/my-feature
wg open feature/my-feature --editor cursor  # Use specific editor
wg open --list-editors                      # Show available editors

# Remove a worktree
wg remove feature/my-feature
wg remove feature/my-feature --force        # Remove even with uncommitted changes
wg remove feature/my-feature --keep-branch  # Keep the git branch
```

## Configuration

Configuration is stored in `.workgarden.yaml`. Run `wg config init` to create a default configuration file.

```yaml
# Example configuration
worktrees:
  base_path: ../worktrees  # Where worktrees are created

docker:
  compose_files:
    - docker-compose.yml

env:
  files:
    - .env.example:.env   # source:destination

editor:
  command: code           # Editor command (code, cursor, zed, etc.)
  auto_open: false        # Open editor automatically on create

hooks:
  post_create: []         # Commands to run after worktree creation
  post_setup: []          # Commands to run after full setup
```
