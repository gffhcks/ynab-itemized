"""Pytest configuration and fixtures."""

from datetime import date
from decimal import Decimal

import pytest

from ynab_itemized.database.manager import DatabaseManager
from ynab_itemized.models.transaction import (
    ItemizedTransaction,
    TransactionItem,
    TransactionStatus,
    YNABTransaction,
)


@pytest.fixture
def sample_ynab_transaction():
    """Sample YNAB transaction for testing."""
    return YNABTransaction(
        ynab_id="test-transaction-123",
        account_id="test-account-456",
        category_id="test-category-789",
        payee_name="Test Store",
        memo="Test purchase",
        amount=Decimal("25000"),  # $25.00 in milliunits
        date=date(2023, 12, 1),
        cleared=TransactionStatus.CLEARED,
        approved=True,
    )


@pytest.fixture
def sample_transaction_items():
    """Sample transaction items for testing."""
    return [
        TransactionItem(
            name="Item 1",
            amount=Decimal("10.99"),
            quantity=1,
            category="Groceries",
            tax_amount=Decimal("0.88"),
        ),
        TransactionItem(
            name="Item 2",
            amount=Decimal("12.50"),
            quantity=2,
            unit_price=Decimal("6.25"),
            category="Groceries",
            tax_amount=Decimal("1.00"),
        ),
    ]


@pytest.fixture
def sample_itemized_transaction(sample_ynab_transaction, sample_transaction_items):
    """Sample itemized transaction for testing."""
    return ItemizedTransaction(
        ynab_transaction=sample_ynab_transaction,
        items=sample_transaction_items,
        subtotal=Decimal("23.49"),
        total_tax=Decimal("1.88"),
        total_discount=Decimal("0.00"),
        tip_amount=Decimal("0.00"),
        store_name="Test Store",
        store_location="123 Test St",
    )


@pytest.fixture
def test_db():
    """Test database manager with in-memory SQLite."""
    db_manager = DatabaseManager("sqlite:///:memory:")
    db_manager.create_tables()
    return db_manager
