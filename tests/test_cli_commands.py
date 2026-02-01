"""Tests for CLI commands."""

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from workgarden.cli.app import app

runner = CliRunner()


class TestCreateCommand:
    """Tests for the create command."""

    def test_create_requires_config(self, temp_git_repo: Path):
        """Test that create fails without config file."""
        os.chdir(temp_git_repo)
        result = runner.invoke(app, ["create", "test-branch"])

        assert result.exit_code == 1
        assert "No .workgarden.yaml found" in result.output

    def test_create_with_dry_run(self, chdir_to_repo: Path):
        """Test create with --dry-run flag."""
        result = runner.invoke(app, ["create", "test-feature", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "SKIPPED" in result.output
        assert "no changes made" in result.output.lower()

    def test_create_success(self, chdir_to_repo: Path):
        """Test successful worktree creation."""
        result = runner.invoke(app, ["create", "test-feature"])

        assert result.exit_code == 0
        assert "Worktree created at" in result.output

    def test_create_duplicate_fails(self, chdir_to_repo: Path):
        """Test that creating duplicate worktree fails."""
        # Create first
        result1 = runner.invoke(app, ["create", "test-feature"])
        assert result1.exit_code == 0

        # Try duplicate
        result2 = runner.invoke(app, ["create", "test-feature"])
        assert result2.exit_code == 1
        assert "already exists" in result2.output

    def test_create_shows_progress(self, chdir_to_repo: Path):
        """Test that create shows progress output."""
        result = runner.invoke(app, ["create", "test-progress"])

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_create_with_no_hooks(self, chdir_to_repo: Path):
        """Test create with --no-hooks flag."""
        result = runner.invoke(app, ["create", "test-skiphooks", "--no-hooks"])

        assert result.exit_code == 0
        # No "Run ... hooks" operations should appear
        assert "run post_create hooks" not in result.output.lower()
        assert "run post_setup hooks" not in result.output.lower()


class TestRemoveCommand:
    """Tests for the remove command."""

    def test_remove_requires_config(self, temp_git_repo: Path):
        """Test that remove fails without config file."""
        os.chdir(temp_git_repo)
        result = runner.invoke(app, ["remove", "test-branch"])

        assert result.exit_code == 1
        assert "No .workgarden.yaml found" in result.output

    def test_remove_nonexistent_fails(self, chdir_to_repo: Path):
        """Test that removing nonexistent worktree fails."""
        result = runner.invoke(app, ["remove", "nonexistent", "-y"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_remove_with_confirmation(self, chdir_to_repo: Path):
        """Test remove with confirmation prompt."""
        # Create worktree first
        runner.invoke(app, ["create", "test-remove"])

        # Remove with confirmation (simulate 'y' input)
        result = runner.invoke(app, ["remove", "test-remove"], input="y\n")

        assert result.exit_code == 0
        assert "Worktree removed" in result.output

    def test_remove_with_yes_flag(self, chdir_to_repo: Path):
        """Test remove with --yes flag skips confirmation."""
        # Create worktree first
        runner.invoke(app, ["create", "test-remove-yes"])

        result = runner.invoke(app, ["remove", "test-remove-yes", "-y"])

        assert result.exit_code == 0
        assert "Worktree removed" in result.output

    def test_remove_cancelled(self, chdir_to_repo: Path):
        """Test remove can be cancelled."""
        # Create worktree first
        runner.invoke(app, ["create", "test-cancel"])

        # Cancel removal
        result = runner.invoke(app, ["remove", "test-cancel"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output

    def test_remove_with_uncommitted_changes_fails(self, chdir_to_repo: Path):
        """Test remove fails with uncommitted changes."""
        # Create worktree
        create_result = runner.invoke(app, ["create", "test-dirty"])
        assert create_result.exit_code == 0

        # Get worktree path from state and add changes
        from workgarden.core.worktree import WorktreeManager

        manager = WorktreeManager()
        worktree = manager.state.get_worktree("test-dirty")
        (worktree.path / "dirty.txt").write_text("uncommitted")

        # Try to remove
        result = runner.invoke(app, ["remove", "test-dirty", "-y"])

        assert result.exit_code == 1
        assert "uncommitted" in result.output.lower()

    def test_remove_force_with_uncommitted_changes(self, chdir_to_repo: Path):
        """Test remove --force works with uncommitted changes."""
        # Create worktree
        create_result = runner.invoke(app, ["create", "test-force"])
        assert create_result.exit_code == 0

        # Get worktree path from state and add changes
        from workgarden.core.worktree import WorktreeManager

        manager = WorktreeManager()
        worktree = manager.state.get_worktree("test-force")
        (worktree.path / "dirty.txt").write_text("uncommitted")

        # Remove with force
        result = runner.invoke(app, ["remove", "test-force", "--force", "-y"])

        assert result.exit_code == 0
        assert "Worktree removed" in result.output


class TestListCommand:
    """Tests for the list command."""

    def test_list_requires_config(self, temp_git_repo: Path):
        """Test that list fails without config file."""
        os.chdir(temp_git_repo)
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "No .workgarden.yaml found" in result.output

    def test_list_empty(self, chdir_to_repo: Path):
        """Test listing with no worktrees."""
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No worktrees found" in result.output

    def test_list_with_worktrees(self, chdir_to_repo: Path):
        """Test listing worktrees shows table."""
        # Create worktrees
        runner.invoke(app, ["create", "feature-one"])
        runner.invoke(app, ["create", "feature-two"])

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "feature-one" in result.output
        assert "feature-two" in result.output
        assert "Branch" in result.output  # Table header
        assert "Path" in result.output
        assert "Status" in result.output

    def test_list_json_output_empty(self, chdir_to_repo: Path):
        """Test JSON output with no worktrees."""
        result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        assert result.output.strip() == "{}"

    def test_list_json_output_with_worktrees(self, chdir_to_repo: Path):
        """Test JSON output with worktrees."""
        # Create worktree
        runner.invoke(app, ["create", "feature-json"])

        result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "feature-json" in data
        assert data["feature-json"]["branch"] == "feature-json"
        assert "path" in data["feature-json"]
        assert "status" in data["feature-json"]

    def test_list_shows_status(self, chdir_to_repo: Path):
        """Test that list shows worktree status."""
        # Create worktree
        create_result = runner.invoke(app, ["create", "feature-status"])
        assert create_result.exit_code == 0

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_list_shows_modified_status(self, chdir_to_repo: Path):
        """Test that list shows Modified status."""
        # Create worktree
        runner.invoke(app, ["create", "feature-modified"])

        # Get worktree path and make changes
        from workgarden.core.worktree import WorktreeManager

        manager = WorktreeManager()
        worktree = manager.state.get_worktree("feature-modified")
        (worktree.path / "change.txt").write_text("modified")

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "Modified" in result.output
