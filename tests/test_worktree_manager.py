"""Tests for WorktreeManager."""

import subprocess
from pathlib import Path

import pytest

from workgarden.core.worktree import CreateOptions, RemoveOptions, WorktreeManager
from workgarden.models.worktree import WorktreeInfo


class TestWorktreeManagerCreate:
    """Tests for WorktreeManager.create()."""

    def test_create_worktree_new_branch(self, temp_git_repo_with_config: Path):
        """Test creating a worktree with a new branch."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)
        options = CreateOptions(branch="feature-test")

        result = manager.create(options)

        assert result.success is True
        assert result.worktree is not None
        assert result.worktree.branch == "feature-test"
        assert result.worktree.path.exists()
        assert manager.state.get_worktree("feature-test") is not None

    def test_create_worktree_existing_branch(self, temp_git_repo_with_config: Path):
        """Test creating a worktree with an existing branch."""
        # Create a branch first
        subprocess.run(
            ["git", "branch", "existing-branch"],
            cwd=temp_git_repo_with_config,
            capture_output=True,
            check=True,
        )

        manager = WorktreeManager(root_path=temp_git_repo_with_config)
        options = CreateOptions(branch="existing-branch")

        result = manager.create(options)

        assert result.success is True
        assert result.worktree.branch == "existing-branch"
        assert result.worktree.path.exists()

    def test_create_worktree_duplicate_fails(self, temp_git_repo_with_config: Path):
        """Test that creating a duplicate worktree fails."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        # Create first worktree
        result1 = manager.create(CreateOptions(branch="feature-test"))
        assert result1.success is True

        # Try to create duplicate
        result2 = manager.create(CreateOptions(branch="feature-test"))
        assert result2.success is False
        assert "already exists" in result2.error

    def test_create_worktree_dry_run(self, temp_git_repo_with_config: Path):
        """Test dry-run mode doesn't create anything."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)
        options = CreateOptions(branch="feature-dry", dry_run=True)

        result = manager.create(options)

        assert result.success is True
        # Worktree should not actually exist
        assert manager.state.get_worktree("feature-dry") is None

    def test_create_worktree_calculates_correct_path(self, temp_git_repo_with_config: Path):
        """Test that worktree path is calculated correctly from config."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)
        options = CreateOptions(branch="feature/my-feature")

        result = manager.create(options)

        assert result.success is True
        # Branch slug should be feature-my-feature
        expected_path = temp_git_repo_with_config.parent / "test-repo-worktrees" / "feature-my-feature"
        assert result.worktree.path == expected_path

    def test_create_worktree_with_progress_callback(self, temp_git_repo_with_config: Path):
        """Test that progress callback is called."""
        progress_calls = []

        def callback(name: str, status: str):
            progress_calls.append((name, status))

        manager = WorktreeManager(
            root_path=temp_git_repo_with_config,
            progress_callback=callback,
        )
        options = CreateOptions(branch="feature-test")

        result = manager.create(options)

        assert result.success is True
        assert len(progress_calls) > 0
        # Check that we got starting and completed for operations
        assert any("starting" in call[1] for call in progress_calls)
        assert any("completed" in call[1] for call in progress_calls)

    def test_create_worktree_skip_hooks(self, temp_git_repo_with_config: Path):
        """Test that skip_hooks option works."""
        progress_calls = []

        def callback(name: str, status: str):
            progress_calls.append((name, status))

        manager = WorktreeManager(
            root_path=temp_git_repo_with_config,
            progress_callback=callback,
        )
        options = CreateOptions(branch="feature-test", skip_hooks=True)

        result = manager.create(options)

        assert result.success is True
        # No "Run ... hooks" operations should be present
        hook_calls = [c for c in progress_calls if "hooks" in c[0].lower()]
        assert len(hook_calls) == 0


class TestWorktreeManagerRemove:
    """Tests for WorktreeManager.remove()."""

    def test_remove_worktree(self, temp_git_repo_with_config: Path):
        """Test removing a worktree."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        # Create first
        create_result = manager.create(CreateOptions(branch="feature-remove"))
        assert create_result.success is True
        worktree_path = create_result.worktree.path

        # Remove
        remove_result = manager.remove(RemoveOptions(branch="feature-remove"))

        assert remove_result.success is True
        assert not worktree_path.exists()
        assert manager.state.get_worktree("feature-remove") is None

    def test_remove_nonexistent_worktree_fails(self, temp_git_repo_with_config: Path):
        """Test that removing nonexistent worktree fails."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        result = manager.remove(RemoveOptions(branch="nonexistent"))

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_remove_worktree_with_uncommitted_changes_fails(
        self, temp_git_repo_with_config: Path
    ):
        """Test that removing worktree with uncommitted changes fails."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        # Create worktree
        create_result = manager.create(CreateOptions(branch="feature-dirty"))
        assert create_result.success is True

        # Make uncommitted changes
        (create_result.worktree.path / "new_file.txt").write_text("changes")

        # Try to remove without force
        remove_result = manager.remove(RemoveOptions(branch="feature-dirty"))

        assert remove_result.success is False
        assert "uncommitted" in remove_result.error.lower()

    def test_remove_worktree_force_with_uncommitted_changes(
        self, temp_git_repo_with_config: Path
    ):
        """Test force removing worktree with uncommitted changes."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        # Create worktree
        create_result = manager.create(CreateOptions(branch="feature-dirty"))
        assert create_result.success is True
        worktree_path = create_result.worktree.path

        # Make uncommitted changes
        (worktree_path / "new_file.txt").write_text("changes")

        # Force remove
        remove_result = manager.remove(RemoveOptions(branch="feature-dirty", force=True))

        assert remove_result.success is True
        assert not worktree_path.exists()

    def test_remove_worktree_keep_branch(self, temp_git_repo_with_config: Path):
        """Test removing worktree but keeping branch."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        # Create worktree
        create_result = manager.create(CreateOptions(branch="feature-keep"))
        assert create_result.success is True

        # Remove with keep_branch
        remove_result = manager.remove(
            RemoveOptions(branch="feature-keep", keep_branch=True)
        )

        assert remove_result.success is True

        # Branch should still exist
        result = subprocess.run(
            ["git", "branch", "--list", "feature-keep"],
            cwd=temp_git_repo_with_config,
            capture_output=True,
            text=True,
        )
        assert "feature-keep" in result.stdout

    def test_remove_worktree_deletes_branch(self, temp_git_repo_with_config: Path):
        """Test removing worktree also deletes branch by default."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        # Create worktree
        create_result = manager.create(CreateOptions(branch="feature-delete"))
        assert create_result.success is True

        # Remove (should delete branch too)
        remove_result = manager.remove(RemoveOptions(branch="feature-delete"))

        assert remove_result.success is True

        # Branch should be deleted
        result = subprocess.run(
            ["git", "branch", "--list", "feature-delete"],
            cwd=temp_git_repo_with_config,
            capture_output=True,
            text=True,
        )
        assert "feature-delete" not in result.stdout


class TestWorktreeManagerList:
    """Tests for WorktreeManager.list()."""

    def test_list_empty(self, temp_git_repo_with_config: Path):
        """Test listing with no worktrees."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        result = manager.list()

        assert result == {}

    def test_list_with_worktrees(self, temp_git_repo_with_config: Path):
        """Test listing multiple worktrees."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        # Create worktrees
        manager.create(CreateOptions(branch="feature-one"))
        manager.create(CreateOptions(branch="feature-two"))

        result = manager.list()

        assert len(result) == 2
        assert "feature-one" in result
        assert "feature-two" in result
        assert result["feature-one"].branch == "feature-one"
        assert result["feature-two"].branch == "feature-two"


class TestWorktreeManagerStatus:
    """Tests for WorktreeManager.get_worktree_status()."""

    def test_status_ok(self, temp_git_repo_with_config: Path):
        """Test status is OK for clean worktree."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        create_result = manager.create(CreateOptions(branch="feature-ok"))
        assert create_result.success is True

        status = manager.get_worktree_status(create_result.worktree)

        assert status == "OK"

    def test_status_modified(self, temp_git_repo_with_config: Path):
        """Test status is Modified for dirty worktree."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        create_result = manager.create(CreateOptions(branch="feature-modified"))
        assert create_result.success is True

        # Make changes
        (create_result.worktree.path / "new_file.txt").write_text("changes")

        status = manager.get_worktree_status(create_result.worktree)

        assert status == "Modified"

    def test_status_missing(self, temp_git_repo_with_config: Path):
        """Test status is Missing for deleted directory."""
        manager = WorktreeManager(root_path=temp_git_repo_with_config)

        create_result = manager.create(CreateOptions(branch="feature-missing"))
        assert create_result.success is True

        # Manually delete the directory (simulating corruption)
        import shutil

        shutil.rmtree(create_result.worktree.path)

        # Create a new WorktreeInfo with the same path to test status
        worktree_info = WorktreeInfo(
            path=create_result.worktree.path,
            branch="feature-missing",
        )

        status = manager.get_worktree_status(worktree_info)

        assert status == "Missing"
