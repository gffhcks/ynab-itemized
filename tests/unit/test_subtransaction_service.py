"""Test SubtransactionService."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from ynab_itemized.models.transaction import (
    ItemizedTransaction,
    TransactionItem,
    YNABSubtransaction,
    YNABTransaction,
)
from ynab_itemized.services.subtransaction import SubtransactionService


@pytest.fixture
def mock_ynab_client():
    """Create a mock YNAB client."""
    return MagicMock()


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    return MagicMock()


@pytest.fixture
def subtransaction_service(mock_ynab_client, mock_db_manager):
    """Create a SubtransactionService instance."""
    return SubtransactionService(mock_ynab_client, mock_db_manager)


@pytest.fixture
def sample_itemized_transaction():
    """Create a sample itemized transaction."""
    return ItemizedTransaction(
        transaction_date=date(2023, 12, 1),
        total_amount=Decimal("25.00"),
        merchant_name="Test Store",
        items=[
            TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
            TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
        ],
    )


class TestCreateSubtransactionsFromItems:
    """Test create_subtransactions_from_items method."""

    def test_create_basic_subtransactions(
        self, subtransaction_service, sample_itemized_transaction
    ):
        """Test creating basic subtransactions from items."""
        subtransactions = subtransaction_service.create_subtransactions_from_items(
            sample_itemized_transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=False,
        )

        assert len(subtransactions) == 2
        assert all(isinstance(st, YNABSubtransaction) for st in subtransactions)

        # Check first item
        assert subtransactions[0].amount == Decimal(
            "-10000"
        )  # $10.00 in milliunits, negative
        assert subtransactions[0].memo == "Item 1"

        # Check second item
        assert subtransactions[1].amount == Decimal(
            "-15000"
        )  # $15.00 in milliunits, negative
        assert subtransactions[1].memo == "Item 2"

    def test_create_subtransactions_with_tax(self, subtransaction_service):
        """Test creating subtransactions with tax."""
        transaction = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("26.50"),
            total_tax=Decimal("1.50"),
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
            ],
        )

        subtransactions = subtransaction_service.create_subtransactions_from_items(
            transaction,
            include_tax_subtransaction=True,
            include_discount_subtransaction=False,
        )

        assert len(subtransactions) == 3

        # Check tax subtransaction
        tax_subtx = subtransactions[2]
        assert tax_subtx.amount == Decimal("-1500")  # $1.50 in milliunits, negative
        assert tax_subtx.memo == "Tax"

    def test_create_subtransactions_with_discount(self, subtransaction_service):
        """Test creating subtransactions with discount."""
        transaction = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("23.00"),
            total_discount=Decimal("2.00"),
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
            ],
        )

        subtransactions = subtransaction_service.create_subtransactions_from_items(
            transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=True,
        )

        assert len(subtransactions) == 3

        # Check discount subtransaction (positive, reduces expense)
        discount_subtx = subtransactions[2]
        assert discount_subtx.amount == Decimal("2000")  # $2.00 in milliunits, positive
        assert discount_subtx.memo == "Discount"

    def test_create_subtransactions_with_tax_and_discount(self, subtransaction_service):
        """Test creating subtransactions with both tax and discount."""
        transaction = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("24.50"),
            total_tax=Decimal("1.50"),
            total_discount=Decimal("2.00"),
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
            ],
        )

        subtransactions = subtransaction_service.create_subtransactions_from_items(
            transaction,
            include_tax_subtransaction=True,
            include_discount_subtransaction=True,
        )

        assert len(subtransactions) == 4
        assert subtransactions[2].memo == "Tax"
        assert subtransactions[3].memo == "Discount"

    def test_subtransactions_sum_to_total(
        self, subtransaction_service, sample_itemized_transaction
    ):
        """Test that subtransactions sum to transaction total."""
        subtransactions = subtransaction_service.create_subtransactions_from_items(
            sample_itemized_transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=False,
        )

        total = sum(st.amount for st in subtransactions)
        expected_total = -int(sample_itemized_transaction.total_amount * 1000)

        assert total == expected_total

    def test_rounding_adjustment(self, subtransaction_service):
        """Test that small rounding errors are adjusted."""
        # Create transaction with amounts that might cause rounding issues
        transaction = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("10.01"),
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("3.34"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("3.34"), quantity=1),
                TransactionItem(name="Item 3", amount=Decimal("3.33"), quantity=1),
            ],
        )

        # Should not raise error, should adjust for rounding
        subtransactions = subtransaction_service.create_subtransactions_from_items(
            transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=False,
        )

        total = sum(st.amount for st in subtransactions)
        expected_total = -int(transaction.total_amount * 1000)

        assert total == expected_total

    def test_large_rounding_error_raises_exception(self, subtransaction_service):
        """Test that large rounding errors raise an exception."""
        # Create transaction where items don't sum to total
        transaction = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("30.00"),  # Total doesn't match items
            merchant_name="Test Store",
            items=[
                TransactionItem(name="Item 1", amount=Decimal("10.00"), quantity=1),
                TransactionItem(name="Item 2", amount=Decimal("15.00"), quantity=1),
            ],
        )

        with pytest.raises(ValueError) as exc_info:
            subtransaction_service.create_subtransactions_from_items(
                transaction,
                include_tax_subtransaction=False,
                include_discount_subtransaction=False,
            )

        assert "don't sum to transaction total" in str(exc_info.value)

    def test_empty_items_list(self, subtransaction_service):
        """Test handling empty items list."""
        transaction = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("0.00"),
            merchant_name="Test Store",
            items=[],
        )

        subtransactions = subtransaction_service.create_subtransactions_from_items(
            transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=False,
        )

        assert len(subtransactions) == 0

    def test_single_item(self, subtransaction_service):
        """Test creating subtransaction from single item."""
        transaction = ItemizedTransaction(
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("10.00"),
            merchant_name="Test Store",
            items=[
                TransactionItem(
                    name="Single Item", amount=Decimal("10.00"), quantity=1
                ),
            ],
        )

        subtransactions = subtransaction_service.create_subtransactions_from_items(
            transaction,
            include_tax_subtransaction=False,
            include_discount_subtransaction=False,
        )

        assert len(subtransactions) == 1
        assert subtransactions[0].amount == Decimal("-10000")
        assert subtransactions[0].memo == "Single Item"


class TestSyncSubtransactionsToYNAB:
    """Test sync_subtransactions_to_ynab method."""

    def test_sync_subtransactions_success(
        self, subtransaction_service, mock_ynab_client
    ):
        """Test successful sync of subtransactions to YNAB."""
        subtransactions = [
            YNABSubtransaction(amount=Decimal("-10000"), memo="Item 1"),
            YNABSubtransaction(amount=Decimal("-15000"), memo="Item 2"),
        ]

        mock_transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("-25000"),
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        mock_ynab_client.update_transaction_with_subtransactions.return_value = (
            mock_transaction
        )

        result = subtransaction_service.sync_subtransactions_to_ynab(
            mock_transaction,
            dry_run=False,
        )

        assert result == mock_transaction
        mock_ynab_client.update_transaction_with_subtransactions.assert_called_once_with(
            mock_transaction
        )

    def test_sync_subtransactions_dry_run(
        self, subtransaction_service, mock_ynab_client
    ):
        """Test dry run mode doesn't actually sync."""
        mock_transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("-25000"),
            date=date(2023, 12, 1),
        )

        result = subtransaction_service.sync_subtransactions_to_ynab(
            mock_transaction,
            dry_run=True,
        )

        assert result is None
        mock_ynab_client.update_transaction_with_subtransactions.assert_not_called()
