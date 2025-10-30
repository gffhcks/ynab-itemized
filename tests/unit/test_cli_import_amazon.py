"""Tests for Amazon import CLI command."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ynab_itemized.cli import main
from ynab_itemized.models.transaction import ItemizedTransaction, TransactionItem


@pytest.fixture
def cli_runner():
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_csv_path():
    """Path to sample Amazon CSV file."""
    return Path(__file__).parent.parent / "fixtures" / "amazon_sample.csv"


@pytest.fixture
def sample_transactions():
    """Sample parsed transactions."""
    return [
        ItemizedTransaction(
            transaction_date=date(2024, 1, 15),
            total_amount=Decimal("35.62"),
            merchant_name="Amazon.com",
            source="amazon",
            source_transaction_id="123-4567890-1234567",
            items=[
                TransactionItem(
                    name="USB-C Cable 6ft", amount=Decimal("12.99"), quantity=1
                ),
                TransactionItem(
                    name="Phone Case Clear", amount=Decimal("19.99"), quantity=1
                ),
            ],
        ),
        ItemizedTransaction(
            transaction_date=date(2024, 2, 3),
            total_amount=Decimal("49.98"),
            merchant_name="Amazon.com",
            source="amazon",
            source_transaction_id="123-7654321-9876543",
            items=[
                TransactionItem(
                    name="Coffee Beans 2lb", amount=Decimal("24.99"), quantity=2
                ),
            ],
        ),
    ]


class TestImportAmazonCommand:
    """Test import-amazon CLI command."""

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.AmazonRequestMyDataIntegration")
    def test_import_amazon_success(
        self,
        mock_integration_class,
        mock_db_class,
        cli_runner,
        sample_csv_path,
        sample_transactions,
    ):
        """Test successful Amazon import."""
        # Setup mocks
        mock_integration = MagicMock()
        mock_integration.parse_data.return_value = sample_transactions
        mock_integration_class.return_value = mock_integration

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run command
        result = cli_runner.invoke(
            main, ["import-amazon", str(sample_csv_path), "--yes"]
        )

        # Verify
        assert result.exit_code == 0
        assert "2 transactions" in result.output
        assert "3 items" in result.output  # 2 items + 1 item = 3 total
        mock_integration.parse_data.assert_called_once_with(str(sample_csv_path))
        assert mock_db.save_itemized_transaction.call_count == 2

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.AmazonRequestMyDataIntegration")
    def test_import_amazon_dry_run(
        self,
        mock_integration_class,
        mock_db_class,
        cli_runner,
        sample_csv_path,
        sample_transactions,
    ):
        """Test dry-run mode (preview only)."""
        # Setup mocks
        mock_integration = MagicMock()
        mock_integration.parse_data.return_value = sample_transactions
        mock_integration_class.return_value = mock_integration

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run command with --dry-run
        result = cli_runner.invoke(
            main, ["import-amazon", str(sample_csv_path), "--dry-run"]
        )

        # Verify
        assert result.exit_code == 0
        assert "DRY RUN" in result.output or "Preview" in result.output
        mock_integration.parse_data.assert_called_once()
        # Should NOT save to database
        mock_db.save_itemized_transaction.assert_not_called()

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.AmazonRequestMyDataIntegration")
    def test_import_amazon_file_not_found(
        self,
        mock_integration_class,
        mock_db_class,
        cli_runner,
    ):
        """Test error when file doesn't exist."""
        # Run command with non-existent file
        result = cli_runner.invoke(
            main, ["import-amazon", "/nonexistent/file.csv", "--yes"]
        )

        # Verify
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.AmazonRequestMyDataIntegration")
    def test_import_amazon_parse_error(
        self,
        mock_integration_class,
        mock_db_class,
        cli_runner,
        sample_csv_path,
    ):
        """Test error handling when parsing fails."""
        # Setup mocks
        mock_integration = MagicMock()
        mock_integration.parse_data.side_effect = ValueError("Invalid CSV format")
        mock_integration_class.return_value = mock_integration

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run command
        result = cli_runner.invoke(
            main, ["import-amazon", str(sample_csv_path), "--yes"]
        )

        # Verify
        assert result.exit_code != 0
        assert "Invalid CSV format" in result.output or "error" in result.output.lower()

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.AmazonRequestMyDataIntegration")
    def test_import_amazon_no_transactions(
        self,
        mock_integration_class,
        mock_db_class,
        cli_runner,
        sample_csv_path,
    ):
        """Test when CSV contains no transactions."""
        # Setup mocks
        mock_integration = MagicMock()
        mock_integration.parse_data.return_value = []
        mock_integration_class.return_value = mock_integration

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run command
        result = cli_runner.invoke(
            main, ["import-amazon", str(sample_csv_path), "--yes"]
        )

        # Verify
        assert result.exit_code == 0
        assert "No transactions" in result.output or "0 transactions" in result.output
        mock_db.save_itemized_transaction.assert_not_called()

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.AmazonRequestMyDataIntegration")
    def test_import_amazon_confirmation_prompt(
        self,
        mock_integration_class,
        mock_db_class,
        cli_runner,
        sample_csv_path,
        sample_transactions,
    ):
        """Test confirmation prompt (without --yes flag)."""
        # Setup mocks
        mock_integration = MagicMock()
        mock_integration.parse_data.return_value = sample_transactions
        mock_integration_class.return_value = mock_integration

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run command without --yes, answer 'n' to prompt
        result = cli_runner.invoke(
            main, ["import-amazon", str(sample_csv_path)], input="n\n"
        )

        # Verify
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()  # Case-insensitive check
        # Should NOT save to database
        mock_db.save_itemized_transaction.assert_not_called()
