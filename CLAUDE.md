# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Workgarden is a CLI tool for managing git worktrees with automatic Docker Compose port allocation, and environment file templating support. The CLI uses `wg` or `workgarden` commands.

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

# Lint with auto-fix
make lint

# Format code
make format
```

## Architecture

**Entry points**: `wg` and `workgarden` commands defined in pyproject.toml, pointing to `workgarden.cli.app:app`

**Transaction-based operations**: WorktreeManager uses a TransactionManager that executes operations in sequence with automatic rollback on failure. Each operation (CreateWorktreeOperation, UpdateStateOperation, RunHookOperation) implements execute() and rollback() methods.

**Current orchestration flow** (WorktreeManager.create):
1. Validate: check if worktree already exists, determine if branch needs creation
2. Calculate worktree path from config templates
3. Build transaction with operations:
   - CreateWorktreeOperation (git worktree add)
   - RunHookOperation for post_create (stub)
   - UpdateStateOperation (add to .workgarden.state.json)
   - RunHookOperation for post_setup (stub)
4. Execute transaction - on any failure, rollback completed operations in reverse

**Key modules**:
- `core/worktree.py` - WorktreeManager orchestrator, TransactionManager, Operation classes
- `config/schema.py` - Pydantic models for .workgarden.yaml
- `config/loader.py` - Config file loading with defaults
- `models/state.py` - StateManager for .workgarden.state.json
- `models/worktree.py` - WorktreeInfo data model
- `utils/git.py` - GitUtils wrapper for git commands
- `utils/root.py` - find_main_repo_root() for worktree-aware root detection
- `utils/template.py` - TemplateContext and variable substitution ({var} for paths, {{VAR}} for content)

**State management**: All worktree metadata stored in `.workgarden.state.json` in the main repo root.

**Planned modules** (not yet implemented): Port allocation, Docker Compose override generation, .env copying with substitution, hook execution.

## Tech Stack

- Python 3.14+ with Typer (CLI), Rich (UI), Pydantic (config validation)
- ruamel.yaml for YAML manipulation (preserves comments)
- Uses `uv` as package manager, `ruff` for linting
