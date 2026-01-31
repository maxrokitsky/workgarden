"""State management for workgarden."""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from workgarden.exceptions import StateError
from workgarden.models.worktree import WorktreeInfo

STATE_FILENAME = ".workgarden.state.json"


class WorkgardenState(BaseModel):
    """State of all managed worktrees."""

    worktrees: dict[str, WorktreeInfo] = Field(default_factory=dict)
    allocated_ports: list[int] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "worktrees": {
                slug: wt.model_dump_json_compatible() for slug, wt in self.worktrees.items()
            },
            "allocated_ports": self.allocated_ports,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkgardenState":
        """Create from dictionary (loaded from JSON)."""
        worktrees = {}
        for slug, wt_data in data.get("worktrees", {}).items():
            worktrees[slug] = WorktreeInfo.from_dict(wt_data)
        return cls(
            worktrees=worktrees,
            allocated_ports=data.get("allocated_ports", []),
        )


class StateManager:
    """Manages the .workgarden.state.json file."""

    def __init__(self, root_path: Path | None = None):
        self.root_path = root_path or Path.cwd()
        self._state: WorkgardenState | None = None

    @property
    def state_path(self) -> Path:
        """Path to the state file."""
        return self.root_path / STATE_FILENAME

    @property
    def state(self) -> WorkgardenState:
        """Get current state, loading if necessary."""
        if self._state is None:
            self._state = self.load()
        return self._state

    def exists(self) -> bool:
        """Check if state file exists."""
        return self.state_path.exists()

    def load(self) -> WorkgardenState:
        """Load state from file, or return empty state if not exists."""
        if not self.exists():
            return WorkgardenState()

        try:
            with open(self.state_path) as f:
                data = json.load(f)
            return WorkgardenState.from_dict(data)
        except json.JSONDecodeError as e:
            raise StateError(f"Invalid JSON in state file: {e}") from e
        except (KeyError, ValueError) as e:
            raise StateError(f"Invalid state file format: {e}") from e

    def save(self) -> None:
        """Save current state to file."""
        if self._state is None:
            return

        with open(self.state_path, "w") as f:
            json.dump(self._state.to_dict(), f, indent=2)

    def add_worktree(self, slug: str, worktree: WorktreeInfo) -> None:
        """Add a worktree to state."""
        self.state.worktrees[slug] = worktree
        for port in worktree.port_mappings.values():
            if port not in self.state.allocated_ports:
                self.state.allocated_ports.append(port)
        self.save()

    def remove_worktree(self, slug: str) -> WorktreeInfo | None:
        """Remove a worktree from state and release its ports."""
        worktree = self.state.worktrees.pop(slug, None)
        if worktree:
            for port in worktree.port_mappings.values():
                if port in self.state.allocated_ports:
                    self.state.allocated_ports.remove(port)
            self.save()
        return worktree

    def get_worktree(self, slug: str) -> WorktreeInfo | None:
        """Get a worktree by slug."""
        return self.state.worktrees.get(slug)

    def list_worktrees(self) -> dict[str, WorktreeInfo]:
        """Get all worktrees."""
        return self.state.worktrees

    def is_port_allocated(self, port: int) -> bool:
        """Check if a port is already allocated."""
        return port in self.state.allocated_ports
