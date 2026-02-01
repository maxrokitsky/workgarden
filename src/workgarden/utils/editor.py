"""Editor detection and launching utilities."""

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from workgarden.exceptions import EditorError


@dataclass
class EditorInfo:
    """Information about an editor."""

    name: str
    command: str
    available: bool


# Known editors with their display names and commands
KNOWN_EDITORS: list[tuple[str, str]] = [
    ("VS Code", "code"),
    ("Cursor", "cursor"),
    ("Zed", "zed"),
    ("Sublime Text", "subl"),
    ("Neovim", "nvim"),
    ("Vim", "vim"),
    ("Emacs", "emacs"),
    ("IntelliJ IDEA", "idea"),
    ("PyCharm", "pycharm"),
]


def detect_available_editors() -> list[EditorInfo]:
    """Detect which known editors are installed.

    Returns:
        List of EditorInfo for all known editors with availability status
    """
    editors = []
    for name, command in KNOWN_EDITORS:
        available = shutil.which(command) is not None
        editors.append(EditorInfo(name=name, command=command, available=available))
    return editors


def get_available_editors() -> list[EditorInfo]:
    """Get list of available (installed) editors.

    Returns:
        List of EditorInfo for installed editors only
    """
    return [e for e in detect_available_editors() if e.available]


def get_default_editor(config_editor: str | None = None) -> str | None:
    """Get the default editor to use.

    Priority order:
    1. Explicit config in .workgarden.yaml (config_editor param)
    2. $VISUAL environment variable
    3. $EDITOR environment variable
    4. First auto-detected editor from known list

    Args:
        config_editor: Editor command from config, if set

    Returns:
        Editor command string, or None if no editor available
    """
    # 1. Config takes priority
    if config_editor:
        return config_editor

    # 2. $VISUAL environment variable
    visual = os.environ.get("VISUAL")
    if visual:
        return visual

    # 3. $EDITOR environment variable
    editor = os.environ.get("EDITOR")
    if editor:
        return editor

    # 4. First available from known editors
    available = get_available_editors()
    if available:
        return available[0].command

    return None


def open_editor(path: Path, editor_command: str | None = None) -> None:
    """Open an editor at the specified path.

    Args:
        path: Directory path to open in the editor
        editor_command: Editor command to use (uses get_default_editor if None)

    Raises:
        EditorError: If no editor is available or launch fails
    """
    command = editor_command or get_default_editor()

    if not command:
        raise EditorError(
            "No editor available. Set editor.command in .workgarden.yaml, "
            "$VISUAL, or $EDITOR environment variable."
        )

    # Parse the command string to handle arguments (e.g., "code --wait")
    command_args = shlex.split(command)
    executable = command_args[0]

    # Verify the editor executable exists
    if not shutil.which(executable):
        raise EditorError(f"Editor executable '{executable}' not found in PATH")

    try:
        # Launch editor as a detached process so it doesn't block the CLI
        subprocess.Popen(
            [*command_args, str(path)],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        raise EditorError(f"Failed to launch editor '{command}': {e}")
