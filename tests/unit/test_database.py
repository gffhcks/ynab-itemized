"""Test database operations."""


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_create_tables(self, test_db):
        """Test table creation."""
        # Tables should be created by the fixture
        assert test_db is not None

    def test_save_ynab_transaction(self, test_db, sample_ynab_transaction):
        """Test saving YNAB transaction."""
        saved = test_db.save_ynab_transaction(sample_ynab_transaction)

        assert saved.ynab_id == sample_ynab_transaction.ynab_id
        assert saved.payee_name == sample_ynab_transaction.payee_name
        assert saved.amount == sample_ynab_transaction.amount

    def test_save_itemized_transaction(self, test_db, sample_itemized_transaction):
        """Test saving complete itemized transaction."""
        saved = test_db.save_itemized_transaction(sample_itemized_transaction)

        assert saved.store_name == sample_itemized_transaction.store_name
        assert len(saved.items) == len(sample_itemized_transaction.items)

    def test_get_itemized_transaction(self, test_db, sample_itemized_transaction):
        """Test retrieving itemized transaction."""
        # Save first
        test_db.save_itemized_transaction(sample_itemized_transaction)

        # Retrieve
        retrieved = test_db.get_itemized_transaction(
            sample_itemized_transaction.ynab_transaction.ynab_id
        )

        assert retrieved is not None
        assert retrieved.store_name == sample_itemized_transaction.store_name
        assert len(retrieved.items) == len(sample_itemized_transaction.items)

    def test_get_nonexistent_transaction(self, test_db):
        """Test retrieving non-existent transaction."""
        result = test_db.get_itemized_transaction("nonexistent-id")
        assert result is None

    def test_delete_itemized_transaction(self, test_db, sample_itemized_transaction):
        """Test deleting itemized transaction."""
        # Save first
        test_db.save_itemized_transaction(sample_itemized_transaction)

        # Delete
        deleted = test_db.delete_itemized_transaction(
            sample_itemized_transaction.ynab_transaction.ynab_id
        )

        assert deleted is True

        # Verify it's gone
        retrieved = test_db.get_itemized_transaction(
            sample_itemized_transaction.ynab_transaction.ynab_id
        )
        assert retrieved is None
