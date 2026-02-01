"""Tests for Operation classes and TransactionManager."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from workgarden.core.worktree import (
    CreateWorktreeOperation,
    Operation,
    OperationStatus,
    RunHookOperation,
    TransactionManager,
    UpdateStateOperation,
)
from workgarden.models.state import StateManager
from workgarden.models.worktree import WorktreeInfo
from workgarden.utils.git import GitUtils
from workgarden.utils.template import TemplateContext


class TestOperationStatus:
    """Tests for OperationStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.IN_PROGRESS.value == "in_progress"
        assert OperationStatus.COMPLETED.value == "completed"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.ROLLED_BACK.value == "rolled_back"
        assert OperationStatus.SKIPPED.value == "skipped"


class TestCreateWorktreeOperation:
    """Tests for CreateWorktreeOperation."""

    def test_execute_calls_worktree_add(self, temp_git_repo: Path):
        """Test that execute calls git worktree_add."""
        git = GitUtils(temp_git_repo)
        worktree_path = temp_git_repo.parent / "worktrees" / "test-branch"

        op = CreateWorktreeOperation(
            git=git,
            path=worktree_path,
            branch="test-branch",
            create_branch=True,
        )

        op.execute()

        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()

    def test_rollback_removes_worktree(self, temp_git_repo: Path):
        """Test that rollback removes the created worktree."""
        git = GitUtils(temp_git_repo)
        worktree_path = temp_git_repo.parent / "worktrees" / "test-branch"

        op = CreateWorktreeOperation(
            git=git,
            path=worktree_path,
            branch="test-branch",
            create_branch=True,
        )

        op.execute()
        assert worktree_path.exists()

        op.rollback()
        assert not worktree_path.exists()

    def test_can_rollback_returns_true(self, temp_git_repo: Path):
        """Test that can_rollback returns True."""
        git = GitUtils(temp_git_repo)
        op = CreateWorktreeOperation(
            git=git,
            path=Path("/tmp/test"),
            branch="test",
            create_branch=True,
        )
        assert op.can_rollback() is True


class TestUpdateStateOperation:
    """Tests for UpdateStateOperation."""

    def test_execute_adds_worktree_to_state(self, temp_git_repo: Path):
        """Test that execute adds worktree to state."""
        state_manager = StateManager(temp_git_repo)
        worktree = WorktreeInfo(
            path=temp_git_repo / "worktrees" / "test",
            branch="test-branch",
        )

        op = UpdateStateOperation(
            state_manager=state_manager,
            slug="test-branch",
            worktree=worktree,
        )

        op.execute()

        assert state_manager.get_worktree("test-branch") is not None
        assert state_manager.get_worktree("test-branch").branch == "test-branch"

    def test_rollback_removes_worktree_from_state(self, temp_git_repo: Path):
        """Test that rollback removes worktree from state."""
        state_manager = StateManager(temp_git_repo)
        worktree = WorktreeInfo(
            path=temp_git_repo / "worktrees" / "test",
            branch="test-branch",
        )

        op = UpdateStateOperation(
            state_manager=state_manager,
            slug="test-branch",
            worktree=worktree,
        )

        op.execute()
        assert state_manager.get_worktree("test-branch") is not None

        op.rollback()
        assert state_manager.get_worktree("test-branch") is None

    def test_can_rollback_returns_true(self, temp_git_repo: Path):
        """Test that can_rollback returns True."""
        state_manager = StateManager(temp_git_repo)
        worktree = WorktreeInfo(
            path=temp_git_repo / "worktrees" / "test",
            branch="test-branch",
        )
        op = UpdateStateOperation(
            state_manager=state_manager,
            slug="test-branch",
            worktree=worktree,
        )
        assert op.can_rollback() is True


class TestRunHookOperation:
    """Tests for RunHookOperation (stub)."""

    def test_execute_is_noop(self):
        """Test that execute is a no-op (stub)."""
        context = TemplateContext(branch="test", branch_slug="test")
        op = RunHookOperation(
            hook_name="post_create",
            hooks=["echo test"],
            context=context,
        )

        # Should not raise
        op.execute()

    def test_can_rollback_returns_false(self):
        """Test that can_rollback returns False (hooks can't be undone)."""
        context = TemplateContext(branch="test", branch_slug="test")
        op = RunHookOperation(
            hook_name="post_create",
            hooks=["echo test"],
            context=context,
        )
        assert op.can_rollback() is False


class TestTransactionManager:
    """Tests for TransactionManager."""

    def test_execute_runs_all_operations(self):
        """Test that execute runs all operations in order."""
        executed = []

        class MockOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                executed.append(self.name)

            def rollback(self):
                pass

        tm = TransactionManager()
        tm.add(MockOp("op1"))
        tm.add(MockOp("op2"))
        tm.add(MockOp("op3"))

        success, error, rollback_errors = tm.execute()

        assert success is True
        assert error is None
        assert rollback_errors == []
        assert executed == ["op1", "op2", "op3"]

    def test_execute_rolls_back_on_failure(self):
        """Test that execute rolls back completed operations on failure."""
        executed = []
        rolled_back = []

        class MockOp(Operation):
            def __init__(self, name: str, should_fail: bool = False):
                super().__init__(name)
                self.should_fail = should_fail

            def execute(self):
                executed.append(self.name)
                if self.should_fail:
                    raise RuntimeError(f"{self.name} failed")

            def rollback(self):
                rolled_back.append(self.name)

        tm = TransactionManager()
        tm.add(MockOp("op1"))
        tm.add(MockOp("op2"))
        tm.add(MockOp("op3", should_fail=True))
        tm.add(MockOp("op4"))

        success, error, rollback_errors = tm.execute()

        assert success is False
        assert "op3 failed" in error
        assert executed == ["op1", "op2", "op3"]
        # Rollback in reverse order, excluding failed op
        assert rolled_back == ["op2", "op1"]

    def test_dry_run_skips_execution(self):
        """Test that dry_run mode skips actual execution."""
        executed = []

        class MockOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                executed.append(self.name)

            def rollback(self):
                pass

        tm = TransactionManager(dry_run=True)
        tm.add(MockOp("op1"))
        tm.add(MockOp("op2"))

        success, error, rollback_errors = tm.execute()

        assert success is True
        assert error is None
        assert executed == []

    def test_progress_callback_is_called(self):
        """Test that progress callback is called for each operation."""
        progress_calls = []

        def progress_callback(name: str, status: str):
            progress_calls.append((name, status))

        class MockOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                pass

            def rollback(self):
                pass

        tm = TransactionManager(progress_callback=progress_callback)
        tm.add(MockOp("op1"))
        tm.add(MockOp("op2"))

        tm.execute()

        assert ("op1", "starting") in progress_calls
        assert ("op1", "completed") in progress_calls
        assert ("op2", "starting") in progress_calls
        assert ("op2", "completed") in progress_calls

    def test_rollback_skips_non_rollbackable_operations(self):
        """Test that rollback skips operations that can't be rolled back."""
        rolled_back = []

        class RollbackableOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                pass

            def rollback(self):
                rolled_back.append(self.name)

            def can_rollback(self):
                return True

        class NonRollbackableOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                pass

            def rollback(self):
                rolled_back.append(self.name)

            def can_rollback(self):
                return False

        class FailingOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                raise RuntimeError("fail")

            def rollback(self):
                pass

        tm = TransactionManager()
        tm.add(RollbackableOp("op1"))
        tm.add(NonRollbackableOp("op2"))
        tm.add(RollbackableOp("op3"))
        tm.add(FailingOp("op4"))

        tm.execute()

        # op2 should not be rolled back because can_rollback() returns False
        assert "op1" in rolled_back
        assert "op2" not in rolled_back
        assert "op3" in rolled_back

    def test_rollback_errors_are_collected(self):
        """Test that rollback errors are collected and returned."""

        class FailingRollbackOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                pass

            def rollback(self):
                raise RuntimeError(f"rollback of {self.name} failed")

        class FailingOp(Operation):
            def __init__(self, name: str):
                super().__init__(name)

            def execute(self):
                raise RuntimeError("fail")

            def rollback(self):
                pass

        tm = TransactionManager()
        tm.add(FailingRollbackOp("op1"))
        tm.add(FailingRollbackOp("op2"))
        tm.add(FailingOp("op3"))

        success, error, rollback_errors = tm.execute()

        assert success is False
        assert len(rollback_errors) == 2
        assert any("op1" in e for e in rollback_errors)
        assert any("op2" in e for e in rollback_errors)
