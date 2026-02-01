"""Tests for root detection utilities."""

import os
from pathlib import Path

import pytest

from workgarden.exceptions import RootDetectionError
from workgarden.utils.root import find_main_repo_root, is_inside_worktree


class TestFindMainRepoRoot:
    """Tests for find_main_repo_root function."""

    def test_from_main_repo(self, temp_git_repo: Path) -> None:
        """Should return the main repo path when called from main repo."""
        result = find_main_repo_root(temp_git_repo)
        assert result == temp_git_repo

    def test_from_worktree(self, temp_git_repo_with_worktree: tuple[Path, Path]) -> None:
        """Should return main repo path when called from a worktree."""
        main_repo, worktree = temp_git_repo_with_worktree
        result = find_main_repo_root(worktree)
        assert result == main_repo

    def test_from_subdirectory_of_main_repo(self, temp_git_repo: Path) -> None:
        """Should return main repo path when called from a subdirectory."""
        subdir = temp_git_repo / "subdir"
        subdir.mkdir()
        result = find_main_repo_root(subdir)
        assert result == temp_git_repo

    def test_from_subdirectory_of_worktree(
        self, temp_git_repo_with_worktree: tuple[Path, Path]
    ) -> None:
        """Should return main repo path when called from subdirectory of worktree."""
        main_repo, worktree = temp_git_repo_with_worktree
        subdir = worktree / "subdir"
        subdir.mkdir()
        result = find_main_repo_root(subdir)
        assert result == main_repo

    def test_not_in_git_repo(self, tmp_path: Path) -> None:
        """Should raise RootDetectionError when not in a git repo."""
        non_git_dir = tmp_path / "not-a-repo"
        non_git_dir.mkdir()
        with pytest.raises(RootDetectionError, match="Not in a git repository"):
            find_main_repo_root(non_git_dir)

    def test_uses_cwd_by_default(self, temp_git_repo: Path) -> None:
        """Should use current working directory when no path provided."""
        original_dir = os.getcwd()
        try:
            os.chdir(temp_git_repo)
            result = find_main_repo_root()
            assert result == temp_git_repo
        finally:
            os.chdir(original_dir)


class TestIsInsideWorktree:
    """Tests for is_inside_worktree function."""

    def test_in_main_repo(self, temp_git_repo: Path) -> None:
        """Should return False when in main repo."""
        result = is_inside_worktree(temp_git_repo)
        assert result is False

    def test_in_worktree(self, temp_git_repo_with_worktree: tuple[Path, Path]) -> None:
        """Should return True when in a worktree."""
        _main_repo, worktree = temp_git_repo_with_worktree
        result = is_inside_worktree(worktree)
        assert result is True

    def test_in_subdirectory_of_main_repo(self, temp_git_repo: Path) -> None:
        """Should return False when in subdirectory of main repo."""
        subdir = temp_git_repo / "subdir"
        subdir.mkdir()
        result = is_inside_worktree(subdir)
        assert result is False

    def test_in_subdirectory_of_worktree(
        self, temp_git_repo_with_worktree: tuple[Path, Path]
    ) -> None:
        """Should return True when in subdirectory of worktree."""
        _main_repo, worktree = temp_git_repo_with_worktree
        subdir = worktree / "subdir"
        subdir.mkdir()
        result = is_inside_worktree(subdir)
        assert result is True

    def test_not_in_git_repo(self, tmp_path: Path) -> None:
        """Should raise RootDetectionError when not in a git repo."""
        non_git_dir = tmp_path / "not-a-repo"
        non_git_dir.mkdir()
        with pytest.raises(RootDetectionError, match="Not in a git repository"):
            is_inside_worktree(non_git_dir)

    def test_uses_cwd_by_default(self, temp_git_repo: Path) -> None:
        """Should use current working directory when no path provided."""
        original_dir = os.getcwd()
        try:
            os.chdir(temp_git_repo)
            result = is_inside_worktree()
            assert result is False
        finally:
            os.chdir(original_dir)


class TestIntegration:
    """Integration tests for root detection with config/state managers."""

    def test_config_loader_from_worktree(
        self, temp_git_repo_with_worktree: tuple[Path, Path]
    ) -> None:
        """ConfigLoader should find config from worktree."""
        from workgarden.config.loader import ConfigLoader

        main_repo, worktree = temp_git_repo_with_worktree
        original_dir = os.getcwd()
        try:
            os.chdir(worktree)
            loader = ConfigLoader()
            assert loader.root_path == main_repo
            assert loader.config_path == main_repo / ".workgarden.yaml"
        finally:
            os.chdir(original_dir)

    def test_state_manager_from_worktree(
        self, temp_git_repo_with_worktree: tuple[Path, Path]
    ) -> None:
        """StateManager should use main repo from worktree."""
        from workgarden.models.state import StateManager

        main_repo, worktree = temp_git_repo_with_worktree
        original_dir = os.getcwd()
        try:
            os.chdir(worktree)
            manager = StateManager()
            assert manager.root_path == main_repo
            assert manager.state_path == main_repo / ".workgarden.state.json"
        finally:
            os.chdir(original_dir)

    def test_worktree_manager_from_worktree(
        self, temp_git_repo_with_worktree: tuple[Path, Path]
    ) -> None:
        """WorktreeManager should use main repo from worktree."""
        from workgarden.core.worktree import WorktreeManager

        main_repo, worktree = temp_git_repo_with_worktree
        original_dir = os.getcwd()
        try:
            os.chdir(worktree)
            manager = WorktreeManager()
            assert manager.root_path == main_repo
        finally:
            os.chdir(original_dir)
