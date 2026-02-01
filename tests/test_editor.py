"""Tests for editor utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from workgarden.exceptions import EditorError
from workgarden.utils.editor import (
    KNOWN_EDITORS,
    EditorInfo,
    detect_available_editors,
    get_available_editors,
    get_default_editor,
    open_editor,
)


class TestDetectAvailableEditors:
    """Tests for detect_available_editors."""

    def test_returns_all_known_editors(self):
        """Should return info for all known editors."""
        with patch("workgarden.utils.editor.shutil.which", return_value=None):
            editors = detect_available_editors()
            assert len(editors) == len(KNOWN_EDITORS)

    def test_marks_installed_editors_as_available(self):
        """Should mark editors found in PATH as available."""

        def mock_which(cmd):
            return "/usr/bin/code" if cmd == "code" else None

        with patch("workgarden.utils.editor.shutil.which", side_effect=mock_which):
            editors = detect_available_editors()
            code_editor = next(e for e in editors if e.command == "code")
            vim_editor = next(e for e in editors if e.command == "vim")

            assert code_editor.available is True
            assert vim_editor.available is False


class TestGetAvailableEditors:
    """Tests for get_available_editors."""

    def test_returns_only_available_editors(self):
        """Should filter to only available editors."""

        def mock_which(cmd):
            return "/usr/bin/code" if cmd in ("code", "vim") else None

        with patch("workgarden.utils.editor.shutil.which", side_effect=mock_which):
            editors = get_available_editors()
            assert all(e.available for e in editors)
            commands = [e.command for e in editors]
            assert "code" in commands
            assert "vim" in commands

    def test_returns_empty_list_when_none_available(self):
        """Should return empty list when no editors installed."""
        with patch("workgarden.utils.editor.shutil.which", return_value=None):
            editors = get_available_editors()
            assert editors == []


class TestGetDefaultEditor:
    """Tests for get_default_editor priority order."""

    def test_config_takes_priority(self):
        """Config editor should take priority over everything."""
        with patch.dict("os.environ", {"VISUAL": "emacs", "EDITOR": "vim"}):
            result = get_default_editor(config_editor="cursor")
            assert result == "cursor"

    def test_visual_env_second_priority(self):
        """$VISUAL should be used when no config."""
        with patch.dict("os.environ", {"VISUAL": "code", "EDITOR": "vim"}):
            result = get_default_editor(config_editor=None)
            assert result == "code"

    def test_editor_env_third_priority(self):
        """$EDITOR should be used when no config or $VISUAL."""
        with patch.dict("os.environ", {"EDITOR": "vim"}, clear=True):
            # Clear VISUAL explicitly
            with patch.dict("os.environ", {"VISUAL": ""}, clear=False):
                import os

                os.environ.pop("VISUAL", None)
                result = get_default_editor(config_editor=None)
                assert result == "vim"

    def test_auto_detect_fourth_priority(self):
        """Should auto-detect when no config or env vars."""

        def mock_which(cmd):
            return "/usr/bin/zed" if cmd == "zed" else None

        with patch.dict("os.environ", {}, clear=True):
            with patch("workgarden.utils.editor.shutil.which", side_effect=mock_which):
                result = get_default_editor(config_editor=None)
                assert result == "zed"

    def test_returns_none_when_nothing_available(self):
        """Should return None when no editor available."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("workgarden.utils.editor.shutil.which", return_value=None):
                result = get_default_editor(config_editor=None)
                assert result is None


class TestOpenEditor:
    """Tests for open_editor."""

    def test_raises_error_when_no_editor(self):
        """Should raise EditorError when no editor available."""
        with patch("workgarden.utils.editor.get_default_editor", return_value=None):
            with pytest.raises(EditorError, match="No editor available"):
                open_editor(Path("/some/path"))

    def test_raises_error_when_editor_not_found(self):
        """Should raise EditorError when editor not in PATH."""
        with patch("workgarden.utils.editor.shutil.which", return_value=None):
            with pytest.raises(EditorError, match="not found in PATH"):
                open_editor(Path("/some/path"), "nonexistent-editor")

    def test_launches_editor_with_popen(self, tmp_path: Path):
        """Should launch editor using subprocess.Popen."""
        mock_popen = MagicMock()

        with patch("workgarden.utils.editor.shutil.which", return_value="/usr/bin/code"):
            with patch("workgarden.utils.editor.subprocess.Popen", mock_popen):
                open_editor(tmp_path, "code")

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        assert call_args[0][0] == ["code", str(tmp_path)]
        assert call_args[1]["start_new_session"] is True

    def test_handles_oserror(self, tmp_path: Path):
        """Should wrap OSError in EditorError."""
        with patch("workgarden.utils.editor.shutil.which", return_value="/usr/bin/code"):
            with patch(
                "workgarden.utils.editor.subprocess.Popen",
                side_effect=OSError("Permission denied"),
            ):
                with pytest.raises(EditorError, match="Failed to launch editor"):
                    open_editor(tmp_path, "code")


class TestEditorInfo:
    """Tests for EditorInfo dataclass."""

    def test_editor_info_creation(self):
        """Should create EditorInfo with correct attributes."""
        info = EditorInfo(name="VS Code", command="code", available=True)
        assert info.name == "VS Code"
        assert info.command == "code"
        assert info.available is True


class TestKnownEditors:
    """Tests for KNOWN_EDITORS constant."""

    def test_known_editors_has_common_editors(self):
        """Should include common editors."""
        commands = [cmd for _, cmd in KNOWN_EDITORS]
        assert "code" in commands
        assert "vim" in commands
        assert "cursor" in commands

    def test_known_editors_format(self):
        """Each entry should be a (name, command) tuple."""
        for entry in KNOWN_EDITORS:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            name, command = entry
            assert isinstance(name, str)
            assert isinstance(command, str)
