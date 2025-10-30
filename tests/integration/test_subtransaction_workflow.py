"""Integration tests for end-to-end subtransaction workflow."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ynab_itemized.database.manager import DatabaseManager
from ynab_itemized.models.transaction import (
    ItemizedTransaction,
    TransactionItem,
    YNABSubtransaction,
    YNABTransaction,
)
from ynab_itemized.services.subtransaction import SubtransactionService
from ynab_itemized.ynab.client import YNABClient


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_manager = DatabaseManager(database_url=f"sqlite:///{db_path}")
        db_manager.create_tables()
        yield db_manager


@pytest.fixture
def mock_ynab_client():
    """Create a mock YNAB client."""
    return MagicMock(spec=YNABClient)


@pytest.fixture
def sample_ynab_transaction():
    """Create a sample YNAB transaction."""
    return YNABTransaction(
        ynab_id="trans-123",
        account_id="account-456",
        amount=Decimal("-25000"),
        date=date(2023, 12, 1),
        payee_name="Test Store",
        memo="Test transaction",
    )


@pytest.fixture
def sample_itemized_transaction(sample_ynab_transaction):
    """Create a sample itemized transaction."""
    return ItemizedTransaction(
        transaction_date=date(2023, 12, 1),
        total_amount=Decimal("25.00"),
        merchant_name="Test Store",
        items=[
            TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
            TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
        ],
        ynab_transaction=sample_ynab_transaction,
    )


class TestEndToEndSubtransactionWorkflow:
    """Test complete end-to-end subtransaction workflow."""

    def test_create_and_sync_subtransactions(
        self, temp_db, mock_ynab_client, sample_itemized_transaction
    ):
        """Test creating subtransactions from items and syncing to YNAB."""
        # Setup
        service = SubtransactionService(mock_ynab_client, temp_db)

        # Save itemized transaction to database
        temp_db.save_itemized_transaction(sample_itemized_transaction)

        # Create subtransactions from items
        subtransactions = service.create_subtransactions_from_items(
            sample_itemized_transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=False,
        )

        # Verify subtransactions created correctly
        assert len(subtransactions) == 2
        assert subtransactions[0].amount == Decimal("-10000")
        assert subtransactions[0].memo == "Item 1"
        assert subtransactions[1].amount == Decimal("-15000")
        assert subtransactions[1].memo == "Item 2"

        # Prepare transaction for sync
        ynab_tx = sample_itemized_transaction.ynab_transaction
        ynab_tx.subtransactions = subtransactions

        # Mock YNAB API response
        updated_tx = YNABTransaction(
            ynab_id=ynab_tx.ynab_id,
            account_id=ynab_tx.account_id,
            amount=ynab_tx.amount,
            date=ynab_tx.date,
            payee_name=ynab_tx.payee_name,
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
        mock_ynab_client.update_transaction_with_subtransactions.return_value = (
            updated_tx
        )

        # Sync to YNAB
        result = service.sync_subtransactions_to_ynab(ynab_tx, dry_run=False)

        # Verify sync was called
        assert result is not None
        assert result.has_subtransactions
        assert len(result.subtransactions) == 2
        mock_ynab_client.update_transaction_with_subtransactions.assert_called_once()

    def test_create_subtransactions_with_tax_and_discount(
        self, temp_db, mock_ynab_client
    ):
        """Test creating subtransactions with tax and discount."""
        # Create transaction with tax and discount
        itemized_tx = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("24.50"),
            total_tax=Decimal("1.50"),
            total_discount=Decimal("2.00"),
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
            ],
            ynab_transaction=YNABTransaction(
                ynab_id="trans-456",
                account_id="account-789",
                amount=Decimal("-24500"),
                date=date(2023, 12, 1),
            ),
        )

        service = SubtransactionService(mock_ynab_client, temp_db)

        # Create subtransactions with tax and discount
        subtransactions = service.create_subtransactions_from_items(
            itemized_tx,
            include_tax_subtransaction=True,
            include_discount_subtransaction=True,
        )

        # Verify all subtransactions created
        assert len(subtransactions) == 4
        assert subtransactions[0].memo == "Item 1"
        assert subtransactions[1].memo == "Item 2"
        assert subtransactions[2].memo == "Tax"
        assert subtransactions[2].amount == Decimal("-1500")
        assert subtransactions[3].memo == "Discount"
        assert subtransactions[3].amount == Decimal(
            "2000"
        )  # Positive (reduces expense)

        # Verify amounts sum correctly
        total = sum(st.amount for st in subtransactions)
        assert total == Decimal("-24500")

    def test_round_trip_save_and_retrieve(
        self, temp_db, mock_ynab_client, sample_ynab_transaction
    ):
        """Test saving itemized transaction and retrieving it."""
        # Create itemized transaction
        itemized_tx = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("25.00"),
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
            ],
            ynab_transaction=YNABTransaction(
                ynab_id="trans-789",
                account_id="account-123",
                amount=Decimal("-25000"),
                date=date(2023, 12, 1),
                payee_name="Test Store",
            ),
        )

        # Save to database
        saved = temp_db.save_itemized_transaction(itemized_tx)

        # Retrieve from database
        retrieved = temp_db.get_itemized_transaction(str(saved.id))

        # Verify transaction retrieved correctly
        assert retrieved is not None
        assert retrieved.ynab_transaction is not None
        assert retrieved.ynab_transaction.ynab_id == "trans-789"
        assert len(retrieved.items) == 2
        assert retrieved.items[0].name == "Item 1"
        assert retrieved.items[1].name == "Item 2"

    def test_dry_run_mode(self, temp_db, mock_ynab_client, sample_itemized_transaction):
        """Test dry-run mode doesn't actually sync to YNAB."""
        service = SubtransactionService(mock_ynab_client, temp_db)

        # Create subtransactions
        subtransactions = service.create_subtransactions_from_items(
            sample_itemized_transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=False,
        )

        # Prepare transaction
        ynab_tx = sample_itemized_transaction.ynab_transaction
        ynab_tx.subtransactions = subtransactions

        # Sync with dry_run=True
        result = service.sync_subtransactions_to_ynab(ynab_tx, dry_run=True)

        # Verify no API call was made
        assert result is None
        mock_ynab_client.update_transaction_with_subtransactions.assert_not_called()

    def test_error_handling_invalid_amounts(self, temp_db, mock_ynab_client):
        """Test error handling when item amounts don't match total."""
        # Create transaction with mismatched amounts
        itemized_tx = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("30.00"),  # Doesn't match items
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
            ],
            ynab_transaction=YNABTransaction(
                ynab_id="trans-999",
                account_id="account-999",
                amount=Decimal("-30000"),
                date=date(2023, 12, 1),
            ),
        )

        service = SubtransactionService(mock_ynab_client, temp_db)

        # Should raise ValueError due to amount mismatch
        with pytest.raises(ValueError) as exc_info:
            service.create_subtransactions_from_items(
                itemized_tx,
                include_tax_subtransaction=False,
                include_discount_subtransaction=False,
            )

        assert "don't sum to transaction total" in str(exc_info.value)
