"""Test CLI commands for subtransaction management."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from ynab_itemized.cli import main
from ynab_itemized.models.transaction import (
    ItemizedTransaction,
    TransactionItem,
    YNABSubtransaction,
    YNABTransaction,
)


@pytest.fixture
def cli_runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_itemized_transaction():
    """Create a sample itemized transaction."""
    return ItemizedTransaction(
        id="itemized-123",
        transaction_date=date(2023, 12, 1),
        total_amount=Decimal("25.00"),
        merchant_name="Test Store",
        items=[
            TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
            TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
        ],
        ynab_transaction=YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("-25000"),
            date=date(2023, 12, 1),
            payee_name="Test Store",
        ),
    )


@pytest.fixture
def sample_ynab_transaction_with_subtransactions():
    """Create a sample YNAB transaction with subtransactions."""
    return YNABTransaction(
        ynab_id="trans-123",
        account_id="account-456",
        amount=Decimal("-25000"),
        date=date(2023, 12, 1),
        payee_name="Test Store",
        subtransactions=[
            YNABSubtransaction(
                subtransaction_id="sub-1",
                amount=Decimal("-10000"),
                memo="Item 1",
            ),
            YNABSubtransaction(
                subtransaction_id="sub-2",
                amount=Decimal("-15000"),
                memo="Item 2",
            ),
        ],
    )


class TestCreateSubtransactionsCommand:
    """Test create-subtransactions CLI command."""

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.YNABClient")
    @patch("ynab_itemized.cli.SubtransactionService")
    def test_create_subtransactions_success(
        self,
        mock_service_class,
        mock_client_class,
        mock_db_class,
        cli_runner,
        sample_itemized_transaction,
        sample_ynab_transaction_with_subtransactions,
    ):
        """Test successful creation of subtransactions."""
        # Setup mocks
        mock_db = MagicMock()
        mock_db.get_itemized_transaction.return_value = sample_itemized_transaction
        mock_db_class.return_value = mock_db

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_service = MagicMock()
        mock_service.create_subtransactions_from_items.return_value = (
            sample_ynab_transaction_with_subtransactions.subtransactions
        )
        mock_service.sync_subtransactions_to_ynab.return_value = (
            sample_ynab_transaction_with_subtransactions
        )
        mock_service_class.return_value = mock_service

        # Run command
        result = cli_runner.invoke(
            main, ["create-subtransactions", "itemized-123", "--yes"]
        )

        # Verify
        assert result.exit_code == 0
        assert "2 subtransactions" in result.output
        mock_service.create_subtransactions_from_items.assert_called_once()
        mock_service.sync_subtransactions_to_ynab.assert_called_once()

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.YNABClient")
    @patch("ynab_itemized.cli.SubtransactionService")
    def test_create_subtransactions_dry_run(
        self,
        mock_service_class,
        mock_client_class,
        mock_db_class,
        cli_runner,
        sample_itemized_transaction,
    ):
        """Test dry-run mode doesn't actually create subtransactions."""
        # Setup mocks
        mock_db = MagicMock()
        mock_db.get_itemized_transaction.return_value = sample_itemized_transaction
        mock_db_class.return_value = mock_db

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_service = MagicMock()
        mock_service.create_subtransactions_from_items.return_value = [
            YNABSubtransaction(amount=Decimal("-10000"), memo="Item 1"),
            YNABSubtransaction(amount=Decimal("-15000"), memo="Item 2"),
        ]
        mock_service.sync_subtransactions_to_ynab.return_value = None
        mock_service_class.return_value = mock_service

        # Run command with dry-run
        result = cli_runner.invoke(
            main, ["create-subtransactions", "itemized-123", "--dry-run"]
        )

        # Verify
        assert result.exit_code == 0
        assert "DRY RUN" in result.output or "preview" in result.output.lower()
        mock_service.create_subtransactions_from_items.assert_called_once()
        # In dry-run mode, sync should NOT be called
        mock_service.sync_subtransactions_to_ynab.assert_not_called()

    @patch("ynab_itemized.cli.DatabaseManager")
    def test_create_subtransactions_transaction_not_found(
        self, mock_db_class, cli_runner
    ):
        """Test error when transaction not found."""
        mock_db = MagicMock()
        mock_db.get_itemized_transaction.return_value = None
        mock_db_class.return_value = mock_db

        result = cli_runner.invoke(
            main, ["create-subtransactions", "nonexistent-id", "--yes"]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.YNABClient")
    @patch("ynab_itemized.cli.SubtransactionService")
    def test_create_subtransactions_with_options(
        self,
        mock_service_class,
        mock_client_class,
        mock_db_class,
        cli_runner,
        sample_itemized_transaction,
    ):
        """Test creating subtransactions with custom options."""
        # Setup mocks
        mock_db = MagicMock()
        mock_db.get_itemized_transaction.return_value = sample_itemized_transaction
        mock_db_class.return_value = mock_db

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_service = MagicMock()
        mock_service.create_subtransactions_from_items.return_value = []
        mock_service_class.return_value = mock_service

        # Run command with options
        result = cli_runner.invoke(
            main,
            [
                "create-subtransactions",
                "itemized-123",
                "--no-tax",
                "--no-discount",
                "--yes",
            ],
        )

        # Verify options were passed
        call_args = mock_service.create_subtransactions_from_items.call_args
        assert call_args[1]["include_tax_subtransaction"] is False
        assert call_args[1]["include_discount_subtransaction"] is False


class TestSyncSubtransactionsCommand:
    """Test sync-subtransactions CLI command."""

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.YNABClient")
    def test_sync_subtransactions_success(
        self,
        mock_client_class,
        mock_db_class,
        cli_runner,
        sample_ynab_transaction_with_subtransactions,
    ):
        """Test successful sync of subtransactions from YNAB."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client.get_transaction.return_value = (
            sample_ynab_transaction_with_subtransactions
        )
        mock_client_class.return_value = mock_client

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run command
        result = cli_runner.invoke(main, ["sync-subtransactions", "trans-123"])

        # Verify
        assert result.exit_code == 0
        assert "2 subtransactions" in result.output
        mock_client.get_transaction.assert_called_once_with("trans-123")
        mock_db.save_ynab_transaction.assert_called_once()

    @patch("ynab_itemized.cli.YNABClient")
    def test_sync_subtransactions_transaction_not_found(
        self, mock_client_class, cli_runner
    ):
        """Test error when transaction not found in YNAB."""
        mock_client = MagicMock()
        mock_client.get_transaction.return_value = None
        mock_client_class.return_value = mock_client

        result = cli_runner.invoke(main, ["sync-subtransactions", "nonexistent-id"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestRemoveSubtransactionsCommand:
    """Test remove-subtransactions CLI command."""

    @patch("ynab_itemized.cli.DatabaseManager")
    @patch("ynab_itemized.cli.YNABClient")
    def test_remove_subtransactions_success(
        self,
        mock_client_class,
        mock_db_class,
        cli_runner,
        sample_ynab_transaction_with_subtransactions,
    ):
        """Test successful removal of subtransactions."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client.get_transaction.return_value = (
            sample_ynab_transaction_with_subtransactions
        )
        mock_client_class.return_value = mock_client

        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run command with confirmation
        result = cli_runner.invoke(
            main, ["remove-subtransactions", "trans-123", "--yes"]
        )

        # Verify
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    @patch("ynab_itemized.cli.YNABClient")
    def test_remove_subtransactions_no_subtransactions(
        self, mock_client_class, cli_runner
    ):
        """Test removing subtransactions when none exist."""
        mock_transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("-25000"),
            date=date(2023, 12, 1),
            subtransactions=[],
        )

        mock_client = MagicMock()
        mock_client.get_transaction.return_value = mock_transaction
        mock_client_class.return_value = mock_client

        result = cli_runner.invoke(
            main, ["remove-subtransactions", "trans-123", "--yes"]
        )

        assert result.exit_code == 0
        assert "no subtransactions" in result.output.lower()
