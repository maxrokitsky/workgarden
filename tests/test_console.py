"""Tests for console utilities."""



from workgarden.utils.console import (
    create_table,
    print_dry_run_banner,
    print_error,
    print_info,
    print_operation_status,
    print_success,
    print_warning,
)


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_print_error(self, capsys):
        """Test print_error outputs to stderr."""
        print_error("test error message")
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "test error message" in captured.err

    def test_print_success(self, capsys):
        """Test print_success outputs success message."""
        print_success("test success")
        captured = capsys.readouterr()
        assert "test success" in captured.out

    def test_print_warning(self, capsys):
        """Test print_warning outputs warning message."""
        print_warning("test warning")
        captured = capsys.readouterr()
        assert "Warning:" in captured.out
        assert "test warning" in captured.out

    def test_print_info(self, capsys):
        """Test print_info outputs info message."""
        print_info("test info")
        captured = capsys.readouterr()
        assert "test info" in captured.out


class TestPrintOperationStatus:
    """Tests for print_operation_status function."""

    def test_status_starting(self, capsys):
        """Test starting status output."""
        print_operation_status("Test operation", "starting")
        captured = capsys.readouterr()
        assert "..." in captured.out
        assert "Test operation" in captured.out

    def test_status_completed(self, capsys):
        """Test completed status output."""
        print_operation_status("Test operation", "completed")
        captured = capsys.readouterr()
        assert "OK" in captured.out
        assert "Test operation" in captured.out

    def test_status_failed(self, capsys):
        """Test failed status output."""
        print_operation_status("Test operation", "failed")
        captured = capsys.readouterr()
        assert "FAILED" in captured.out
        assert "Test operation" in captured.out

    def test_status_rolling_back(self, capsys):
        """Test rolling_back status output."""
        print_operation_status("Test operation", "rolling_back")
        captured = capsys.readouterr()
        assert "ROLLBACK" in captured.out
        assert "Test operation" in captured.out

    def test_status_skipped(self, capsys):
        """Test skipped status output."""
        print_operation_status("Test operation", "skipped")
        captured = capsys.readouterr()
        assert "SKIPPED" in captured.out
        assert "Test operation" in captured.out


class TestPrintDryRunBanner:
    """Tests for print_dry_run_banner function."""

    def test_dry_run_banner(self, capsys):
        """Test dry run banner output."""
        print_dry_run_banner()
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "No changes will be made" in captured.out


class TestCreateTable:
    """Tests for create_table function."""

    def test_create_table_with_columns(self):
        """Test creating a table with columns."""
        table = create_table("Test Table", ["Col1", "Col2", "Col3"])

        assert table.title == "Test Table"
        assert len(table.columns) == 3

    def test_create_table_can_add_rows(self):
        """Test that rows can be added to the table."""
        table = create_table("Test", ["A", "B"])
        table.add_row("val1", "val2")

        assert table.row_count == 1
