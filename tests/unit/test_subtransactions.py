"""Test subtransaction functionality."""

from datetime import date
from decimal import Decimal

import pytest

from ynab_itemized.models.transaction import (
    TransactionStatus,
    YNABSubtransaction,
    YNABTransaction,
)


class TestYNABSubtransaction:
    """Test YNABSubtransaction model."""

    def test_create_basic_subtransaction(self):
        """Test creating a basic subtransaction."""
        subtransaction = YNABSubtransaction(
            amount=Decimal("10000"),  # $10.00 in milliunits
            memo="Groceries",
            category_id="cat-123",
        )

        assert subtransaction.amount == Decimal("10000")
        assert subtransaction.memo == "Groceries"
        assert subtransaction.category_id == "cat-123"
        assert subtransaction.subtransaction_id is None
        assert subtransaction.deleted is False

    def test_create_subtransaction_with_all_fields(self):
        """Test creating a subtransaction with all fields."""
        subtransaction = YNABSubtransaction(
            subtransaction_id="sub-123",
            amount=Decimal("15000"),
            memo="Electronics",
            payee_id="payee-456",
            payee_name="Best Buy",
            category_id="cat-789",
            category_name="Electronics & Software",
            deleted=False,
        )

        assert subtransaction.subtransaction_id == "sub-123"
        assert subtransaction.amount == Decimal("15000")
        assert subtransaction.memo == "Electronics"
        assert subtransaction.payee_id == "payee-456"
        assert subtransaction.payee_name == "Best Buy"
        assert subtransaction.category_id == "cat-789"
        assert subtransaction.category_name == "Electronics & Software"
        assert subtransaction.deleted is False

    def test_subtransaction_amount_conversion(self):
        """Test that amount is properly converted to Decimal."""
        # Test with int
        sub1 = YNABSubtransaction(amount=10000)
        assert isinstance(sub1.amount, Decimal)
        assert sub1.amount == Decimal("10000")

        # Test with float
        sub2 = YNABSubtransaction(amount=10000.0)
        assert isinstance(sub2.amount, Decimal)
        assert sub2.amount == Decimal("10000")

        # Test with string
        sub3 = YNABSubtransaction(amount="10000")
        assert isinstance(sub3.amount, Decimal)
        assert sub3.amount == Decimal("10000")

    def test_transfer_subtransaction(self):
        """Test creating a transfer subtransaction."""
        subtransaction = YNABSubtransaction(
            amount=Decimal("50000"),
            transfer_account_id="account-789",
            transfer_transaction_id="trans-456",
        )

        assert subtransaction.amount == Decimal("50000")
        assert subtransaction.transfer_account_id == "account-789"
        assert subtransaction.transfer_transaction_id == "trans-456"


class TestYNABTransactionWithSubtransactions:
    """Test YNABTransaction model with subtransactions."""

    def test_transaction_without_subtransactions(self):
        """Test transaction without subtransactions."""
        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
        )

        assert transaction.has_subtransactions is False
        assert len(transaction.subtransactions) == 0
        assert transaction.validate_subtransaction_amounts() is True

    def test_transaction_with_valid_subtransactions(self):
        """Test transaction with valid subtransactions that sum correctly."""
        subtransactions = [
            YNABSubtransaction(
                amount=Decimal("10000"),
                memo="Groceries",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                amount=Decimal("15000"),
                memo="Gas",
                category_id="cat-gas",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),  # Sum of subtransactions
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        assert transaction.has_subtransactions is True
        assert len(transaction.subtransactions) == 2
        assert transaction.validate_subtransaction_amounts() is True

    def test_transaction_with_invalid_subtransaction_sum(self):
        """Test transaction where subtransactions don't sum to total."""
        subtransactions = [
            YNABSubtransaction(
                amount=Decimal("10000"),
                memo="Groceries",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                amount=Decimal("12000"),  # Sum is 22000, not 25000
                memo="Gas",
                category_id="cat-gas",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        assert transaction.has_subtransactions is True
        assert transaction.validate_subtransaction_amounts() is False

    def test_transaction_with_three_subtransactions(self):
        """Test transaction split into three categories."""
        subtransactions = [
            YNABSubtransaction(
                amount=Decimal("5000"),
                memo="Milk",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                amount=Decimal("10000"),
                memo="Bread",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                amount=Decimal("10000"),
                memo="Cleaning supplies",
                category_id="cat-household",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        assert transaction.has_subtransactions is True
        assert len(transaction.subtransactions) == 3
        assert transaction.validate_subtransaction_amounts() is True

    def test_transaction_with_negative_amounts(self):
        """Test transaction with negative amounts (refunds/returns)."""
        subtransactions = [
            YNABSubtransaction(
                amount=Decimal("-5000"),
                memo="Returned item",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                amount=Decimal("-3000"),
                memo="Refund",
                category_id="cat-household",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("-8000"),  # Total refund
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        assert transaction.has_subtransactions is True
        assert transaction.validate_subtransaction_amounts() is True

    def test_empty_subtransactions_list(self):
        """Test transaction with empty subtransactions list."""
        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
            subtransactions=[],
        )

        assert transaction.has_subtransactions is False
        assert transaction.validate_subtransaction_amounts() is True

    def test_subtransaction_with_payee_override(self):
        """Test subtransaction with different payee than parent."""
        subtransactions = [
            YNABSubtransaction(
                amount=Decimal("25000"),
                memo="Reimbursement",
                payee_id="payee-different",
                payee_name="Different Payee",
                category_id="cat-reimbursement",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            payee_name="Original Payee",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        assert transaction.payee_name == "Original Payee"
        assert transaction.subtransactions[0].payee_name == "Different Payee"
        assert transaction.validate_subtransaction_amounts() is True


class TestSubtransactionEdgeCases:
    """Test edge cases for subtransactions."""

    def test_zero_amount_subtransaction(self):
        """Test subtransaction with zero amount."""
        subtransaction = YNABSubtransaction(
            amount=Decimal("0"),
            memo="Zero amount",
            category_id="cat-123",
        )

        assert subtransaction.amount == Decimal("0")

    def test_very_large_amount(self):
        """Test subtransaction with very large amount."""
        subtransaction = YNABSubtransaction(
            amount=Decimal("999999999"),  # $999,999.999
            memo="Large purchase",
            category_id="cat-123",
        )

        assert subtransaction.amount == Decimal("999999999")

    def test_subtransaction_with_only_required_field(self):
        """Test subtransaction with only the required amount field."""
        subtransaction = YNABSubtransaction(amount=Decimal("10000"))

        assert subtransaction.amount == Decimal("10000")
        assert subtransaction.memo is None
        assert subtransaction.category_id is None
        assert subtransaction.payee_id is None
