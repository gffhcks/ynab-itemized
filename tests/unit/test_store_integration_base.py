"""Tests for store integration base classes."""

from abc import ABC
from datetime import date
from decimal import Decimal

import pytest

from ynab_itemized.integrations.base import StoreIntegration
from ynab_itemized.models.transaction import ItemizedTransaction


class TestStoreIntegration:
    """Test StoreIntegration abstract base class."""

    def test_store_integration_is_abstract(self):
        """Test that StoreIntegration cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StoreIntegration(config={})

    def test_concrete_implementation_requires_methods(self):
        """Test that concrete implementations must implement abstract methods."""

        class IncompleteStore(StoreIntegration):
            """Incomplete implementation missing required methods."""

            pass

        with pytest.raises(TypeError):
            IncompleteStore(config={})

    def test_concrete_implementation_with_all_methods(self):
        """Test that concrete implementation with all methods can be instantiated."""

        class CompleteStore(StoreIntegration):
            """Complete implementation with all required methods."""

            @property
            def store_name(self) -> str:
                return "TestStore"

            @property
            def integration_type(self) -> str:
                return "test"

            def parse_data(self, raw_data) -> list[ItemizedTransaction]:
                return []

        store = CompleteStore(config={"test": "value"})
        assert store.store_name == "TestStore"
        assert store.integration_type == "test"
        assert store.config == {"test": "value"}

    def test_get_supported_date_range_default(self):
        """Test default supported date range."""

        class TestStore(StoreIntegration):
            @property
            def store_name(self) -> str:
                return "Test"

            @property
            def integration_type(self) -> str:
                return "test"

            def parse_data(self, raw_data) -> list[ItemizedTransaction]:
                return []

        store = TestStore(config={})
        assert store.get_supported_date_range() == 90

    def test_get_supported_date_range_override(self):
        """Test overriding supported date range."""

        class TestStore(StoreIntegration):
            @property
            def store_name(self) -> str:
                return "Test"

            @property
            def integration_type(self) -> str:
                return "test"

            def parse_data(self, raw_data) -> list[ItemizedTransaction]:
                return []

            def get_supported_date_range(self) -> int:
                return 365

        store = TestStore(config={})
        assert store.get_supported_date_range() == 365
