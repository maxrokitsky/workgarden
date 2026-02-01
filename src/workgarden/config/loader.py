"""Configuration loader for .workgarden.yaml."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from workgarden.config.schema import WorkgardenConfig
from workgarden.exceptions import ConfigNotFoundError, ConfigValidationError
from workgarden.utils.root import find_main_repo_root

CONFIG_FILENAME = ".workgarden.yaml"


class ConfigLoader:
    """Loads and manages workgarden configuration."""

    def __init__(self, root_path: Path | None = None):
        self.root_path = root_path or find_main_repo_root()
        self._config: WorkgardenConfig | None = None

    @property
    def config_path(self) -> Path:
        """Path to the config file."""
        return self.root_path / CONFIG_FILENAME

    @property
    def config(self) -> WorkgardenConfig:
        """Get loaded config, loading if necessary."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

    def load(self) -> WorkgardenConfig:
        """Load configuration from file."""
        if not self.exists():
            raise ConfigNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path) as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in config file: {e}") from e

        try:
            return WorkgardenConfig.model_validate(data)
        except ValidationError as e:
            raise ConfigValidationError(f"Config validation failed: {e}") from e

    def save(self, config: WorkgardenConfig) -> None:
        """Save configuration to file."""
        from ruamel.yaml import YAML

        ruamel = YAML()
        ruamel.default_flow_style = False
        ruamel.indent(mapping=2, sequence=4, offset=2)

        with open(self.config_path, "w") as f:
            ruamel.dump(config.to_yaml_dict(), f)

        self._config = config


def load_config(root_path: Path | None = None) -> WorkgardenConfig:
    """Convenience function to load config."""
    return ConfigLoader(root_path).load()
