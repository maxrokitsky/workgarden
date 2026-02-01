"""Tests for HookRunner and lifecycle hooks."""

from pathlib import Path

import pytest

from workgarden.core.hooks import HookResult, HookRunner, HookRunnerResult
from workgarden.exceptions import HookError
from workgarden.utils.template import TemplateContext


class TestHookResult:
    """Tests for HookResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful hook result."""
        result = HookResult(
            command="echo hello",
            success=True,
            stdout="hello\n",
            stderr="",
            return_code=0,
        )
        assert result.success is True
        assert result.command == "echo hello"
        assert result.stdout == "hello\n"
        assert result.return_code == 0

    def test_failed_result(self):
        """Test creating a failed hook result."""
        result = HookResult(
            command="false",
            success=False,
            stderr="error message",
            return_code=1,
        )
        assert result.success is False
        assert result.return_code == 1

    def test_result_with_error(self):
        """Test creating a result with error message."""
        result = HookResult(
            command="cmd",
            success=False,
            error="Command timed out",
        )
        assert result.success is False
        assert result.error == "Command timed out"


class TestHookRunnerResult:
    """Tests for HookRunnerResult dataclass."""

    def test_empty_results(self):
        """Test runner result with no hooks."""
        result = HookRunnerResult(hook_name="post_create", success=True)
        assert result.hook_name == "post_create"
        assert result.success is True
        assert result.results == []

    def test_with_results(self):
        """Test runner result with hook results."""
        hook_results = [
            HookResult(command="echo 1", success=True, return_code=0),
            HookResult(command="echo 2", success=True, return_code=0),
        ]
        result = HookRunnerResult(
            hook_name="post_setup",
            success=True,
            results=hook_results,
        )
        assert len(result.results) == 2


class TestHookRunner:
    """Tests for HookRunner class."""

    def test_run_empty_hooks_list(self, tmp_path: Path):
        """Test that running empty hooks list succeeds."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_create", [])

        assert result.success is True
        assert result.hook_name == "post_create"
        assert result.results == []

    def test_run_single_hook(self, tmp_path: Path):
        """Test running a single hook command."""
        context = TemplateContext(branch="test-branch", branch_slug="test-branch")
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_create", ["echo hello"])

        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].success is True
        assert "hello" in result.results[0].stdout

    def test_run_multiple_hooks(self, tmp_path: Path):
        """Test running multiple hook commands."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_setup", ["echo first", "echo second", "echo third"])

        assert result.success is True
        assert len(result.results) == 3
        assert all(r.success for r in result.results)

    def test_variable_substitution(self, tmp_path: Path):
        """Test that {{VARIABLE}} placeholders are substituted."""
        context = TemplateContext(
            branch="feature/my-branch",
            branch_slug="feature-my-branch",
            worktree_path=tmp_path,
            repo_name="test-repo",
        )
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_create", ["echo {{BRANCH}} {{BRANCH_SLUG}} {{REPO_NAME}}"])

        assert result.success is True
        assert "feature/my-branch" in result.results[0].stdout
        assert "feature-my-branch" in result.results[0].stdout
        assert "test-repo" in result.results[0].stdout

    def test_port_variable_substitution(self, tmp_path: Path):
        """Test that PORT_* variables are substituted."""
        context = TemplateContext(
            branch="test",
            branch_slug="test",
            port_mappings={"web": 8080, "db": 5432},
        )
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_setup", ["echo {{PORT_WEB}} {{PORT_DB}}"])

        assert result.success is True
        assert "8080" in result.results[0].stdout
        assert "5432" in result.results[0].stdout

    def test_environment_variables_exposed(self, tmp_path: Path):
        """Test that WG_* environment variables are exposed to hooks."""
        context = TemplateContext(
            branch="test-branch",
            branch_slug="test-branch",
            repo_name="my-repo",
        )
        runner = HookRunner(context=context, working_dir=tmp_path)

        # Use printenv to check environment variables
        result = runner.run("post_create", ["printenv WG_BRANCH"])

        assert result.success is True
        assert "test-branch" in result.results[0].stdout

    def test_all_wg_environment_variables(self, tmp_path: Path):
        """Test that all expected WG_* variables are set."""
        context = TemplateContext(
            branch="test",
            branch_slug="test-slug",
            worktree_path=tmp_path,
            repo_name="repo",
            port_mappings={"api": 3000},
        )
        runner = HookRunner(context=context, working_dir=tmp_path)

        # Create a script to check all variables
        script = """
        echo "BRANCH=$WG_BRANCH"
        echo "SLUG=$WG_BRANCH_SLUG"
        echo "REPO=$WG_REPO_NAME"
        echo "PORT=$WG_PORT_API"
        """
        result = runner.run("test", [f"bash -c '{script}'"])

        assert result.success is True
        output = result.results[0].stdout
        assert "BRANCH=test" in output
        assert "SLUG=test-slug" in output
        assert "REPO=repo" in output
        assert "PORT=3000" in output

    def test_fail_fast_on_error(self, tmp_path: Path):
        """Test that execution stops on first failure."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path)

        # Create a marker file to track execution
        marker = tmp_path / "marker.txt"

        with pytest.raises(HookError) as exc_info:
            runner.run(
                "post_create",
                [
                    "echo first",
                    "exit 1",  # This should fail
                    f"touch {marker}",  # This should not run
                ],
            )

        assert "post_create hook failed" in str(exc_info.value)
        assert not marker.exists()  # Third command should not have run

    def test_hook_error_includes_command(self, tmp_path: Path):
        """Test that HookError includes the failed command."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path)

        with pytest.raises(HookError) as exc_info:
            runner.run("post_setup", ["this-command-does-not-exist-12345"])

        assert "this-command-does-not-exist-12345" in str(exc_info.value)

    def test_runs_in_working_directory(self, tmp_path: Path):
        """Test that commands run in the specified working directory."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_create", ["pwd"])

        assert result.success is True
        assert str(tmp_path) in result.results[0].stdout

    def test_working_dir_defaults_to_worktree_path(self, tmp_path: Path):
        """Test that working_dir defaults to context.worktree_path."""
        context = TemplateContext(
            branch="test",
            branch_slug="test",
            worktree_path=tmp_path,
        )
        runner = HookRunner(context=context)

        result = runner.run("post_create", ["pwd"])

        assert result.success is True
        assert str(tmp_path) in result.results[0].stdout

    def test_timeout_handling(self, tmp_path: Path):
        """Test that commands timeout correctly."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path, timeout=1)

        with pytest.raises(HookError) as exc_info:
            runner.run("post_create", ["sleep 10"])

        assert "timed out" in str(exc_info.value).lower()

    def test_stderr_captured(self, tmp_path: Path):
        """Test that stderr is captured."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_create", ["bash -c 'echo error >&2'"])

        assert result.success is True
        assert "error" in result.results[0].stderr

    def test_creates_files(self, tmp_path: Path):
        """Test that hooks can create files in working directory."""
        context = TemplateContext(branch="test", branch_slug="test")
        runner = HookRunner(context=context, working_dir=tmp_path)

        result = runner.run("post_setup", ["touch .setup_complete"])

        assert result.success is True
        assert (tmp_path / ".setup_complete").exists()

    def test_complex_command_with_substitution(self, tmp_path: Path):
        """Test complex command with multiple substitutions."""
        context = TemplateContext(
            branch="feature/add-auth",
            branch_slug="feature-add-auth",
            worktree_path=tmp_path,
            repo_name="myapp",
        )
        runner = HookRunner(context=context, working_dir=tmp_path)

        # Create a file with branch info
        result = runner.run(
            "post_create",
            ["echo 'Branch: {{BRANCH}} in {{REPO_NAME}}' > branch_info.txt"],
        )

        assert result.success is True
        content = (tmp_path / "branch_info.txt").read_text()
        assert "feature/add-auth" in content
        assert "myapp" in content


class TestHookRunnerWithGitRepo:
    """Tests for HookRunner with actual git repository."""

    def test_runs_in_worktree_directory(self, temp_git_repo: Path):
        """Test that hooks run in the worktree directory."""
        context = TemplateContext(
            branch="test",
            branch_slug="test",
            worktree_path=temp_git_repo,
        )
        runner = HookRunner(context=context, working_dir=temp_git_repo)

        result = runner.run("post_create", ["git rev-parse --show-toplevel"])

        assert result.success is True
        # The output should contain the repo path
        assert str(temp_git_repo) in result.results[0].stdout

    def test_can_run_git_commands(self, temp_git_repo: Path):
        """Test that hooks can run git commands."""
        context = TemplateContext(
            branch="test",
            branch_slug="test",
            worktree_path=temp_git_repo,
        )
        runner = HookRunner(context=context, working_dir=temp_git_repo)

        result = runner.run("post_create", ["git status"])

        assert result.success is True
        assert (
            "nothing to commit" in result.results[0].stdout.lower()
            or "clean" in result.results[0].stdout.lower()
        )
