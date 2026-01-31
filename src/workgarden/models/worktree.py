"""Worktree information model."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class WorktreeInfo(BaseModel):
    """Information about a managed worktree."""

    path: Path
    branch: str
    created_at: datetime = Field(default_factory=datetime.now)
    port_mappings: dict[str, int] = Field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Get branch slug (used as worktree directory name)."""
        return self.branch.replace("/", "-").replace("_", "-").lower()

    def model_dump_json_compatible(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "path": str(self.path),
            "branch": self.branch,
            "created_at": self.created_at.isoformat(),
            "port_mappings": self.port_mappings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorktreeInfo":
        """Create from dictionary (loaded from JSON)."""
        return cls(
            path=Path(data["path"]),
            branch=data["branch"],
            created_at=datetime.fromisoformat(data["created_at"]),
            port_mappings=data.get("port_mappings", {}),
        )
