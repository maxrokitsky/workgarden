"""Utilities for finding the main repository root."""

import subprocess
from pathlib import Path

from workgarden.exceptions import RootDetectionError


def find_main_repo_root(start_path: Path | None = None) -> Path:
    """Find main repo from any location (main repo or worktree).

    Uses git rev-parse --git-common-dir to find the shared .git directory,
    which always points to the main repo even when run from a worktree.

    Args:
        start_path: Starting directory for detection. Defaults to current working directory.

    Returns:
        Path to the main repository root.

    Raises:
        RootDetectionError: If not in a git repository.
    """
    cwd = start_path or Path.cwd()

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        git_common_dir = result.stdout.strip()
    except subprocess.CalledProcessError:
        raise RootDetectionError("Not in a git repository")

    # git-common-dir returns the path to the shared .git directory
    # For main repo: ".git"
    # For worktree: "/absolute/path/to/main-repo/.git"
    git_common_path = Path(git_common_dir)

    # If it's a relative path (like ".git"), resolve it relative to cwd
    if not git_common_path.is_absolute():
        git_common_path = (cwd / git_common_path).resolve()

    # The main repo root is the parent of the .git directory
    return git_common_path.parent


def is_inside_worktree(start_path: Path | None = None) -> bool:
    """Check if the current directory is inside a worktree (not main repo).

    Args:
        start_path: Starting directory for detection. Defaults to current working directory.

    Returns:
        True if inside a worktree, False if in main repo.

    Raises:
        RootDetectionError: If not in a git repository.
    """
    cwd = start_path or Path.cwd()

    try:
        # Get git-dir (current repo's .git path)
        git_dir_result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        git_dir = git_dir_result.stdout.strip()

        # Get git-common-dir (shared .git directory)
        git_common_result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        git_common_dir = git_common_result.stdout.strip()
    except subprocess.CalledProcessError:
        raise RootDetectionError("Not in a git repository")

    # Resolve both to absolute paths for comparison
    git_dir_path = Path(git_dir)
    git_common_path = Path(git_common_dir)

    if not git_dir_path.is_absolute():
        git_dir_path = (cwd / git_dir_path).resolve()
    if not git_common_path.is_absolute():
        git_common_path = (cwd / git_common_path).resolve()

    # In a worktree, git-dir points to .git/worktrees/<name>
    # while git-common-dir points to the main repo's .git
    # They're different if we're in a worktree
    return git_dir_path != git_common_path
