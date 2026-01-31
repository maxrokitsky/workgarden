"""Git utilities."""

import subprocess
from pathlib import Path

from workgarden.exceptions import GitError


class GitUtils:
    """Git operations helper."""

    def __init__(self, repo_path: Path | None = None):
        self.repo_path = repo_path or Path.cwd()

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command."""
        cmd = ["git", "-C", str(self.repo_path), *args]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=check)
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command failed: {e.stderr.strip()}") from e

    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        result = self._run("rev-parse", "--git-dir", check=False)
        return result.returncode == 0

    def get_repo_name(self) -> str:
        """Get the repository name from remote or directory."""
        result = self._run("remote", "get-url", "origin", check=False)
        if result.returncode == 0:
            url = result.stdout.strip()
            name = url.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            return name
        return self.repo_path.name

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self._run("branch", "--show-current")
        return result.stdout.strip()

    def branch_exists(self, branch: str) -> bool:
        """Check if a branch exists (local or remote)."""
        result = self._run("show-ref", "--verify", f"refs/heads/{branch}", check=False)
        if result.returncode == 0:
            return True
        result = self._run("show-ref", "--verify", f"refs/remotes/origin/{branch}", check=False)
        return result.returncode == 0

    def get_worktree_list(self) -> list[dict]:
        """Get list of all git worktrees."""
        result = self._run("worktree", "list", "--porcelain")
        worktrees = []
        current: dict = {}

        for line in result.stdout.strip().split("\n"):
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
                continue

            if line.startswith("worktree "):
                current["path"] = line[9:]
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:].replace("refs/heads/", "")
            elif line == "bare":
                current["bare"] = True
            elif line == "detached":
                current["detached"] = True

        if current:
            worktrees.append(current)

        return worktrees

    def worktree_add(self, path: Path, branch: str, create_branch: bool = False) -> None:
        """Add a new worktree."""
        args = ["worktree", "add"]
        if create_branch:
            args.extend(["-b", branch, str(path)])
        else:
            args.extend([str(path), branch])
        self._run(*args)

    def worktree_remove(self, path: Path, force: bool = False) -> None:
        """Remove a worktree."""
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(path))
        self._run(*args)

    def delete_branch(self, branch: str, force: bool = False) -> None:
        """Delete a local branch."""
        args = ["branch", "-D" if force else "-d", branch]
        self._run(*args)

    def has_uncommitted_changes(self, path: Path) -> bool:
        """Check if worktree has uncommitted changes."""
        result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())


def get_branch_slug(branch: str) -> str:
    """Convert branch name to slug for directory naming."""
    return branch.replace("/", "-").replace("_", "-").lower()
