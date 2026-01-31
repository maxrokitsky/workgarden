# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Workgarden is a CLI tool for managing git worktrees with automatic Docker Compose port allocation, environment file templating, and Claude Code configuration support. The CLI uses `wg` or `workgarden` commands.

## Commands

```bash
# Run CLI during development
uv run wg <command>

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run single test
uv run pytest tests/test_file.py::test_name -v
```

## Architecture

**Entry points**: `wg` and `workgarden` commands defined in pyproject.toml, pointing to `workgarden.cli.app:app`

**Core orchestration flow** (WorktreeManager.create):
1. Load config (.workgarden.yaml) and state (.workgarden.state.json)
2. Create git worktree
3. Run post_create hooks
4. Scan docker-compose for ports (parse ${VAR} syntax)
5. Allocate free ports via socket bind check
6. Generate docker-compose.override.worktree.yml
7. Copy .env files with variable substitution ({{BRANCH}}, {{PORT_*}}, etc.)
8. Copy .claude config
9. Update state file
10. Run post_setup hooks
11. On error: rollback all steps in reverse order

**Key modules**:
- `core/worktree.py` - Main orchestrator with create/remove/list
- `core/ports.py` - Port allocation via socket bind, tracks in state
- `core/docker.py` - Parses compose files, generates override (never modifies original)
- `core/environment.py` - Copies .env with {{VARIABLE}} substitution
- `config/schema.py` - Pydantic models for .workgarden.yaml
- `models/state.py` - StateManager for .workgarden.state.json

**State management**: All worktree metadata and allocated ports stored in `.workgarden.state.json` in the main repo.

## Tech Stack

- Python with Typer (CLI), Rich (UI), Pydantic (config validation)
- ruamel.yaml for YAML manipulation (preserves comments)
- Uses `uv` as package manager
