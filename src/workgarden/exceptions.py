"""Custom exceptions for Workgarden."""


class WorkgardenError(Exception):
    """Base exception for Workgarden."""


class ConfigError(WorkgardenError):
    """Configuration related errors."""


class ConfigNotFoundError(ConfigError):
    """Config file not found."""


class ConfigValidationError(ConfigError):
    """Config validation failed."""


class StateError(WorkgardenError):
    """State file related errors."""


class GitError(WorkgardenError):
    """Git operation errors."""


class WorktreeError(WorkgardenError):
    """Worktree operation errors."""


class WorktreeExistsError(WorktreeError):
    """Worktree already exists."""


class WorktreeNotFoundError(WorktreeError):
    """Worktree not found."""


class PortError(WorkgardenError):
    """Port allocation errors."""


class NoAvailablePortError(PortError):
    """No available ports in range."""


class HookError(WorkgardenError):
    """Hook execution errors."""


class RootDetectionError(WorkgardenError):
    """Failed to detect repository root."""


class EditorError(WorkgardenError):
    """Editor-related errors."""
