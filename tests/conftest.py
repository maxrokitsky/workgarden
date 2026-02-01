"""Shared pytest fixtures for workgarden tests."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with initial commit."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    return repo_path


@pytest.fixture
def temp_git_repo_with_config(temp_git_repo: Path) -> Path:
    """Create a temporary git repository with workgarden config."""
    config_content = """\
version: "1.0"
worktree_base_path: "../{repo_name}-worktrees"
worktree_naming: "{branch_slug}"
environment:
  copy_files:
    - ".env"
  substitutions:
    enabled: true
    custom_variables: {}
docker_compose:
  files:
    - "docker-compose.yml"
  ports:
    base_port: 10000
    max_port: 65000
    named_mappings: {}
hooks:
  post_create: []
  post_setup: []
  pre_remove: []
  post_remove: []
claude:
  copy_config: true
  copy_items:
    - "settings.json"
    - "commands/"
"""
    (temp_git_repo / ".workgarden.yaml").write_text(config_content)
    return temp_git_repo


@pytest.fixture
def chdir_to_repo(temp_git_repo_with_config: Path):
    """Change directory to the test repo for the duration of the test."""
    original_dir = os.getcwd()
    os.chdir(temp_git_repo_with_config)
    yield temp_git_repo_with_config
    os.chdir(original_dir)
