"""Tests for Amazon Request My Data integration."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ynab_itemized.integrations.amazon import AmazonRequestMyDataIntegration
from ynab_itemized.models.transaction import ItemizedTransaction, TransactionItem


@pytest.fixture
def sample_csv_path():
    """Path to sample Amazon CSV file."""
    return Path(__file__).parent.parent / "fixtures" / "amazon_sample.csv"


@pytest.fixture
def amazon_integration():
    """Create Amazon integration instance."""
    return AmazonRequestMyDataIntegration(config={})


class TestAmazonRequestMyDataIntegration:
    """Test Amazon Request My Data CSV parsing."""

    def test_store_name(self, amazon_integration):
        """Test store name property."""
        assert amazon_integration.store_name == "Amazon"

    def test_integration_type(self, amazon_integration):
        """Test integration type property."""
        assert amazon_integration.integration_type == "csv"

    def test_supported_date_range(self, amazon_integration):
        """Test supported date range (Amazon provides all history)."""
        # Amazon Request My Data provides all order history
        assert amazon_integration.get_supported_date_range() >= 3650  # 10+ years

    def test_parse_csv_file(self, amazon_integration, sample_csv_path):
        """Test parsing Amazon CSV file."""
        transactions = amazon_integration.parse_csv_file(sample_csv_path)

        # Should group items by order ID
        assert len(transactions) == 2  # 2 unique orders

        # Check first transaction (2 items)
        tx1 = transactions[0]
        assert tx1.transaction_date == date(2024, 1, 15)
        assert tx1.merchant_name == "Amazon.com"
        assert tx1.source == "amazon"
        assert tx1.source_transaction_id == "123-4567890-1234567"
        assert len(tx1.items) == 2
        assert tx1.total_amount == Decimal("35.62")  # 14.03 + 21.59
        assert tx1.total_tax == Decimal("2.64")  # 1.04 + 1.60

        # Check items
        item1 = tx1.items[0]
        assert item1.name == "USB-C Cable 6ft"
        assert item1.amount == Decimal("12.99")
        assert item1.quantity == 1
        assert item1.tax_amount == Decimal("1.04")
        assert item1.metadata["asin"] == "B08ABCD1234"
        assert item1.metadata["category"] == "ELECTRONICS"

        item2 = tx1.items[1]
        assert item2.name == "Phone Case Clear"
        assert item2.amount == Decimal("19.99")
        assert item2.quantity == 1
        assert item2.tax_amount == Decimal("1.60")

        # Check second transaction (1 item with quantity 2)
        tx2 = transactions[1]
        assert tx2.transaction_date == date(2024, 2, 3)
        assert tx2.source_transaction_id == "123-7654321-9876543"
        assert len(tx2.items) == 1
        assert tx2.total_amount == Decimal("49.98")
        assert tx2.total_tax == Decimal("0.00")

        item3 = tx2.items[0]
        assert item3.name == "Coffee Beans 2lb"
        assert item3.amount == Decimal("24.99")
        assert item3.quantity == 2
        assert item3.unit_price == Decimal("24.99")

    def test_parse_empty_csv(self, amazon_integration, tmp_path):
        """Test parsing empty CSV file."""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text(
            "Order Date,Order ID,Title,Category,ASIN/ISBN,Purchase Price Per Unit,Quantity,Item Subtotal,Item Subtotal Tax,Item Total\n"
        )

        transactions = amazon_integration.parse_csv_file(empty_csv)
        assert transactions == []

    def test_parse_csv_with_missing_columns(self, amazon_integration, tmp_path):
        """Test parsing CSV with missing required columns."""
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("Order Date,Title\n01/15/2024,USB Cable\n")

        with pytest.raises(ValueError) as exc_info:
            amazon_integration.parse_csv_file(bad_csv)

        assert "Missing required columns" in str(exc_info.value)

    def test_parse_csv_with_invalid_date(self, amazon_integration, tmp_path):
        """Test parsing CSV with invalid date format."""
        bad_csv = tmp_path / "bad_date.csv"
        bad_csv.write_text(
            "Order Date,Order ID,Title,Purchase Price Per Unit,Quantity,Item Subtotal,Item Subtotal Tax,Item Total\n"
            "invalid-date,123-456,USB Cable,12.99,1,12.99,1.04,14.03\n"
        )

        with pytest.raises(ValueError) as exc_info:
            amazon_integration.parse_csv_file(bad_csv)

        assert "Invalid date format" in str(exc_info.value)

    def test_parse_csv_with_invalid_amount(self, amazon_integration, tmp_path):
        """Test parsing CSV with invalid amount."""
        bad_csv = tmp_path / "bad_amount.csv"
        bad_csv.write_text(
            "Order Date,Order ID,Title,Purchase Price Per Unit,Quantity,Item Subtotal,Item Subtotal Tax,Item Total\n"
            "01/15/2024,123-456,USB Cable,invalid,1,12.99,1.04,14.03\n"
        )

        with pytest.raises(ValueError) as exc_info:
            amazon_integration.parse_csv_file(bad_csv)

        assert "Invalid amount" in str(exc_info.value)

    def test_parse_data_method(self, amazon_integration, sample_csv_path):
        """Test parse_data method (reads file and parses)."""
        # parse_data should accept file path as raw_data
        transactions = amazon_integration.parse_data(str(sample_csv_path))

        assert len(transactions) == 2
        assert all(isinstance(tx, ItemizedTransaction) for tx in transactions)

    def test_group_items_by_order(self, amazon_integration):
        """Test grouping items by order ID."""
        rows = [
            {
                "Order Date": "01/15/2024",
                "Order ID": "123-456",
                "Title": "Item 1",
                "Purchase Price Per Unit": "10.00",
                "Quantity": "1",
                "Item Subtotal": "10.00",
                "Item Subtotal Tax": "0.80",
                "Item Total": "10.80",
            },
            {
                "Order Date": "01/15/2024",
                "Order ID": "123-456",
                "Title": "Item 2",
                "Purchase Price Per Unit": "15.00",
                "Quantity": "1",
                "Item Subtotal": "15.00",
                "Item Subtotal Tax": "1.20",
                "Item Total": "16.20",
            },
            {
                "Order Date": "01/16/2024",
                "Order ID": "789-012",
                "Title": "Item 3",
                "Purchase Price Per Unit": "20.00",
                "Quantity": "1",
                "Item Subtotal": "20.00",
                "Item Subtotal Tax": "1.60",
                "Item Total": "21.60",
            },
        ]

        grouped = amazon_integration._group_items_by_order(rows)

        assert len(grouped) == 2
        assert "123-456" in grouped
        assert "789-012" in grouped
        assert len(grouped["123-456"]) == 2
        assert len(grouped["789-012"]) == 1

    def test_parse_order_creates_itemized_transaction(self, amazon_integration):
        """Test parsing a single order into ItemizedTransaction."""
        order_items = [
            {
                "Order Date": "01/15/2024",
                "Order ID": "123-456",
                "Title": "USB Cable",
                "Category": "ELECTRONICS",
                "ASIN/ISBN": "B08ABC123",
                "Purchase Price Per Unit": "12.99",
                "Quantity": "1",
                "Item Subtotal": "12.99",
                "Item Subtotal Tax": "1.04",
                "Item Total": "14.03",
                "Website": "Amazon.com",
            }
        ]

        transaction = amazon_integration._parse_order("123-456", order_items)

        assert isinstance(transaction, ItemizedTransaction)
        assert transaction.transaction_date == date(2024, 1, 15)
        assert transaction.merchant_name == "Amazon.com"
        assert transaction.source == "amazon"
        assert transaction.source_transaction_id == "123-456"
        assert transaction.total_amount == Decimal("14.03")
        assert transaction.total_tax == Decimal("1.04")
        assert len(transaction.items) == 1

        item = transaction.items[0]
        assert item.name == "USB Cable"
        assert item.amount == Decimal("12.99")
        assert item.quantity == 1
        assert item.tax_amount == Decimal("1.04")
        assert item.metadata["asin"] == "B08ABC123"
        assert item.metadata["category"] == "ELECTRONICS"

    def test_parse_order_with_multiple_items(self, amazon_integration):
        """Test parsing order with multiple items."""
        order_items = [
            {
                "Order Date": "01/15/2024",
                "Order ID": "123-456",
                "Title": "Item 1",
                "Purchase Price Per Unit": "10.00",
                "Quantity": "1",
                "Item Subtotal": "10.00",
                "Item Subtotal Tax": "0.80",
                "Item Total": "10.80",
                "Website": "Amazon.com",
            },
            {
                "Order Date": "01/15/2024",
                "Order ID": "123-456",
                "Title": "Item 2",
                "Purchase Price Per Unit": "15.00",
                "Quantity": "2",
                "Item Subtotal": "30.00",
                "Item Subtotal Tax": "2.40",
                "Item Total": "32.40",
                "Website": "Amazon.com",
            },
        ]

        transaction = amazon_integration._parse_order("123-456", order_items)

        assert len(transaction.items) == 2
        assert transaction.total_amount == Decimal("43.20")  # 10.80 + 32.40
        assert transaction.total_tax == Decimal("3.20")  # 0.80 + 2.40
        assert transaction.items[1].quantity == 2
        assert transaction.items[1].unit_price == Decimal("15.00")
