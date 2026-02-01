"""Pydantic models for .workgarden.yaml configuration."""

from pydantic import BaseModel, Field


class SubstitutionsConfig(BaseModel):
    """Environment variable substitution settings."""

    enabled: bool = True
    custom_variables: dict[str, str] = Field(default_factory=dict)


class EnvironmentConfig(BaseModel):
    """Environment file handling configuration."""

    copy_files: list[str] = Field(default_factory=lambda: [".env"])
    substitutions: SubstitutionsConfig = Field(default_factory=SubstitutionsConfig)


class PortsConfig(BaseModel):
    """Port allocation configuration."""

    base_port: int = 10000
    max_port: int = 65000
    named_mappings: dict[str, str] = Field(default_factory=dict)


class DockerComposeConfig(BaseModel):
    """Docker Compose configuration."""

    files: list[str] = Field(default_factory=lambda: ["docker-compose.yml"])
    ports: PortsConfig = Field(default_factory=PortsConfig)


class HooksConfig(BaseModel):
    """Lifecycle hooks configuration."""

    post_create: list[str] = Field(default_factory=list)
    post_setup: list[str] = Field(default_factory=list)
    pre_remove: list[str] = Field(default_factory=list)
    post_remove: list[str] = Field(default_factory=list)


class EditorConfig(BaseModel):
    """Editor configuration."""

    command: str | None = None  # e.g., "code", "cursor"
    auto_open: bool = False  # Open automatically on create


class WorkgardenConfig(BaseModel):
    """Root configuration model for .workgarden.yaml."""

    version: str = "1.0"
    worktree_base_path: str = "../{repo_name}-worktrees"
    worktree_naming: str = "{branch_slug}"
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    docker_compose: DockerComposeConfig = Field(default_factory=DockerComposeConfig)
    hooks: HooksConfig = Field(default_factory=HooksConfig)
    editor: EditorConfig = Field(default_factory=EditorConfig)

    def to_yaml_dict(self) -> dict:
        """Convert to dictionary suitable for YAML output."""
        return self.model_dump(mode="json")


DEFAULT_CONFIG = WorkgardenConfig()
