"""Test data models."""

from datetime import date
from decimal import Decimal

from ynab_itemized.models.transaction import (
    TransactionItem,
    TransactionStatus,
    YNABTransaction,
)


class TestTransactionItem:
    """Test TransactionItem model."""

    def test_create_basic_item(self):
        """Test creating a basic transaction item."""
        item = TransactionItem(name="Test Item", amount=Decimal("10.99"))

        assert item.name == "Test Item"
        assert item.amount == Decimal("10.99")
        assert item.quantity == 1
        assert item.discount_amount == Decimal("0")
        assert item.tax_amount == Decimal("0")

    def test_unit_price_calculation(self):
        """Test automatic unit price calculation."""
        item = TransactionItem(name="Test Item", amount=Decimal("20.00"), quantity=4)

        assert item.unit_price == Decimal("5.00")

    def test_amount_validation_with_quantity_and_unit_price(self):
        """Test amount validation against quantity and unit price."""
        item = TransactionItem(
            name="Test Item",
            amount=Decimal("15.00"),
            quantity=3,
            unit_price=Decimal("5.00"),
        )

        # Should not raise validation error
        assert item.amount == Decimal("15.00")


class TestYNABTransaction:
    """Test YNABTransaction model."""

    def test_create_ynab_transaction(self):
        """Test creating a YNAB transaction."""
        transaction = YNABTransaction(
            ynab_id="test-123",
            account_id="account-456",
            payee_name="Test Store",
            amount=Decimal("25000"),  # milliunits
            date=date(2023, 12, 1),
        )

        assert transaction.ynab_id == "test-123"
        assert transaction.account_id == "account-456"
        assert transaction.payee_name == "Test Store"
        assert transaction.amount == Decimal("25000")
        assert transaction.date == date(2023, 12, 1)
        assert transaction.cleared == TransactionStatus.UNCLEARED
        assert transaction.approved is True


class TestItemizedTransaction:
    """Test ItemizedTransaction model."""

    def test_calculated_properties(self, sample_itemized_transaction):
        """Test calculated property methods."""
        transaction = sample_itemized_transaction

        assert transaction.calculated_subtotal == Decimal("23.49")
        assert transaction.calculated_tax == Decimal("1.88")
        assert transaction.calculated_discount == Decimal("0.00")
        assert transaction.calculated_total == Decimal("25.37")

    def test_validate_totals_success(self, sample_itemized_transaction):
        """Test successful total validation."""
        # Adjust YNAB amount to match calculated total
        sample_itemized_transaction.ynab_transaction.amount = Decimal(
            "25370"
        )  # $25.37 in milliunits

        assert sample_itemized_transaction.validate_totals() is True

    def test_validate_totals_failure(self, sample_itemized_transaction):
        """Test failed total validation."""
        # YNAB amount doesn't match calculated total
        sample_itemized_transaction.ynab_transaction.amount = Decimal(
            "30000"
        )  # $30.00 in milliunits

        assert sample_itemized_transaction.validate_totals() is False
