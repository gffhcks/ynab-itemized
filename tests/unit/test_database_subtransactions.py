"""Test database schema for subtransaction support."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from ynab_itemized.database.models import (
    Base,
    ItemizedTransactionDB,
    TransactionItemDB,
    YNABTransactionDB,
)


@pytest.fixture
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestYNABTransactionDBSchema:
    """Test YNABTransactionDB schema changes."""

    def test_has_subtransactions_field_exists(self, db_session):
        """Test that has_subtransactions field exists."""
        inspector = inspect(db_session.bind)
        columns = {
            col["name"]: col for col in inspector.get_columns("ynab_transactions")
        }

        assert "has_subtransactions" in columns
        assert columns["has_subtransactions"]["type"].__class__.__name__ == "BOOLEAN"
        assert columns["has_subtransactions"]["nullable"] is False

    def test_has_subtransactions_default_value(self, db_session):
        """Test that has_subtransactions defaults to False."""
        transaction = YNABTransactionDB(
            id="test-id-1",
            ynab_id="ynab-123",
            account_id="account-456",
            amount=Decimal("25.00"),
            date=date(2023, 12, 1),
            cleared="cleared",
            approved=True,
        )

        db_session.add(transaction)
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(YNABTransactionDB).filter_by(id="test-id-1").first()
        )
        assert retrieved.has_subtransactions is False

    def test_has_subtransactions_can_be_set_true(self, db_session):
        """Test that has_subtransactions can be set to True."""
        transaction = YNABTransactionDB(
            id="test-id-2",
            ynab_id="ynab-456",
            account_id="account-789",
            amount=Decimal("50.00"),
            date=date(2023, 12, 1),
            cleared="cleared",
            approved=True,
            has_subtransactions=True,
        )

        db_session.add(transaction)
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(YNABTransactionDB).filter_by(id="test-id-2").first()
        )
        assert retrieved.has_subtransactions is True

    def test_update_has_subtransactions(self, db_session):
        """Test updating has_subtransactions field."""
        transaction = YNABTransactionDB(
            id="test-id-3",
            ynab_id="ynab-789",
            account_id="account-123",
            amount=Decimal("75.00"),
            date=date(2023, 12, 1),
            cleared="cleared",
            approved=True,
            has_subtransactions=False,
        )

        db_session.add(transaction)
        db_session.commit()

        # Update to True
        transaction.has_subtransactions = True
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(YNABTransactionDB).filter_by(id="test-id-3").first()
        )
        assert retrieved.has_subtransactions is True


class TestItemizedTransactionDBSchema:
    """Test ItemizedTransactionDB schema changes."""

    def test_subtransactions_synced_at_field_exists(self, db_session):
        """Test that subtransactions_synced_at field exists."""
        inspector = inspect(db_session.bind)
        columns = {
            col["name"]: col for col in inspector.get_columns("itemized_transactions")
        }

        assert "subtransactions_synced_at" in columns
        assert (
            columns["subtransactions_synced_at"]["type"].__class__.__name__
            == "DATETIME"
        )
        assert columns["subtransactions_synced_at"]["nullable"] is True

    def test_subtransactions_synced_at_default_null(self, db_session):
        """Test that subtransactions_synced_at defaults to NULL."""
        transaction = ItemizedTransactionDB(
            id="test-id-1",
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("25.00"),
            match_status="unmatched",
            source="test",
        )

        db_session.add(transaction)
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(ItemizedTransactionDB).filter_by(id="test-id-1").first()
        )
        assert retrieved.subtransactions_synced_at is None

    def test_subtransactions_synced_at_can_be_set(self, db_session):
        """Test that subtransactions_synced_at can be set."""
        sync_time = datetime(2023, 12, 1, 10, 30, 0)
        transaction = ItemizedTransactionDB(
            id="test-id-2",
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("50.00"),
            match_status="matched",
            source="test",
            subtransactions_synced_at=sync_time,
        )

        db_session.add(transaction)
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(ItemizedTransactionDB).filter_by(id="test-id-2").first()
        )
        assert retrieved.subtransactions_synced_at == sync_time

    def test_update_subtransactions_synced_at(self, db_session):
        """Test updating subtransactions_synced_at field."""
        transaction = ItemizedTransactionDB(
            id="test-id-3",
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("75.00"),
            match_status="matched",
            source="test",
        )

        db_session.add(transaction)
        db_session.commit()

        # Update sync time
        sync_time = datetime(2023, 12, 1, 15, 45, 0)
        transaction.subtransactions_synced_at = sync_time
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(ItemizedTransactionDB).filter_by(id="test-id-3").first()
        )
        assert retrieved.subtransactions_synced_at == sync_time


class TestTransactionItemDBSchema:
    """Test TransactionItemDB schema changes."""

    def test_ynab_subtransaction_id_field_exists(self, db_session):
        """Test that ynab_subtransaction_id field exists."""
        inspector = inspect(db_session.bind)
        columns = {
            col["name"]: col for col in inspector.get_columns("transaction_items")
        }

        assert "ynab_subtransaction_id" in columns
        assert columns["ynab_subtransaction_id"]["type"].__class__.__name__ == "VARCHAR"
        assert columns["ynab_subtransaction_id"]["nullable"] is True

    def test_ynab_category_id_field_exists(self, db_session):
        """Test that ynab_category_id field exists."""
        inspector = inspect(db_session.bind)
        columns = {
            col["name"]: col for col in inspector.get_columns("transaction_items")
        }

        assert "ynab_category_id" in columns
        assert columns["ynab_category_id"]["type"].__class__.__name__ == "VARCHAR"
        assert columns["ynab_category_id"]["nullable"] is True

    def test_ynab_subtransaction_id_index_exists(self, db_session):
        """Test that index on ynab_subtransaction_id exists."""
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("transaction_items")

        index_names = [idx["name"] for idx in indexes]
        assert "ix_transaction_items_ynab_subtransaction_id" in index_names

        # Find the specific index
        subtrans_index = next(
            idx
            for idx in indexes
            if idx["name"] == "ix_transaction_items_ynab_subtransaction_id"
        )
        assert "ynab_subtransaction_id" in subtrans_index["column_names"]

    def test_transaction_item_without_subtransaction_mapping(self, db_session):
        """Test creating item without subtransaction mapping."""
        # First create parent transaction
        parent = ItemizedTransactionDB(
            id="parent-1",
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("25.00"),
            match_status="unmatched",
            source="test",
        )
        db_session.add(parent)
        db_session.commit()

        # Create item
        item = TransactionItemDB(
            id="item-1",
            transaction_id="parent-1",
            name="Test Item",
            amount=Decimal("10.99"),
            quantity=1,
        )

        db_session.add(item)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(TransactionItemDB).filter_by(id="item-1").first()
        assert retrieved.ynab_subtransaction_id is None
        assert retrieved.ynab_category_id is None

    def test_transaction_item_with_subtransaction_mapping(self, db_session):
        """Test creating item with subtransaction mapping."""
        # First create parent transaction
        parent = ItemizedTransactionDB(
            id="parent-2",
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("25.00"),
            match_status="matched",
            source="test",
        )
        db_session.add(parent)
        db_session.commit()

        # Create item with subtransaction mapping
        item = TransactionItemDB(
            id="item-2",
            transaction_id="parent-2",
            name="Groceries",
            amount=Decimal("10.99"),
            quantity=1,
            ynab_subtransaction_id="sub-123",
            ynab_category_id="cat-groceries",
        )

        db_session.add(item)
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(TransactionItemDB).filter_by(id="item-2").first()
        assert retrieved.ynab_subtransaction_id == "sub-123"
        assert retrieved.ynab_category_id == "cat-groceries"

    def test_query_items_by_subtransaction_id(self, db_session):
        """Test querying items by subtransaction ID (uses index)."""
        # Create parent transaction
        parent = ItemizedTransactionDB(
            id="parent-3",
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("50.00"),
            match_status="matched",
            source="test",
        )
        db_session.add(parent)
        db_session.commit()

        # Create multiple items
        items = [
            TransactionItemDB(
                id="item-3a",
                transaction_id="parent-3",
                name="Item A",
                amount=Decimal("10.00"),
                ynab_subtransaction_id="sub-123",
            ),
            TransactionItemDB(
                id="item-3b",
                transaction_id="parent-3",
                name="Item B",
                amount=Decimal("20.00"),
                ynab_subtransaction_id="sub-456",
            ),
            TransactionItemDB(
                id="item-3c",
                transaction_id="parent-3",
                name="Item C",
                amount=Decimal("20.00"),
                ynab_subtransaction_id="sub-123",
            ),
        ]

        for item in items:
            db_session.add(item)
        db_session.commit()

        # Query by subtransaction ID
        results = (
            db_session.query(TransactionItemDB)
            .filter_by(ynab_subtransaction_id="sub-123")
            .all()
        )

        assert len(results) == 2
        assert {r.id for r in results} == {"item-3a", "item-3c"}

    def test_update_subtransaction_mapping(self, db_session):
        """Test updating subtransaction mapping on existing item."""
        # Create parent transaction
        parent = ItemizedTransactionDB(
            id="parent-4",
            transaction_date=date(2023, 12, 1),
            total_amount=Decimal("25.00"),
            match_status="matched",
            source="test",
        )
        db_session.add(parent)
        db_session.commit()

        # Create item without mapping
        item = TransactionItemDB(
            id="item-4",
            transaction_id="parent-4",
            name="Test Item",
            amount=Decimal("10.99"),
        )
        db_session.add(item)
        db_session.commit()

        # Update with subtransaction mapping
        item.ynab_subtransaction_id = "sub-789"
        item.ynab_category_id = "cat-household"
        db_session.commit()

        # Retrieve and verify
        retrieved = db_session.query(TransactionItemDB).filter_by(id="item-4").first()
        assert retrieved.ynab_subtransaction_id == "sub-789"
        assert retrieved.ynab_category_id == "cat-household"
