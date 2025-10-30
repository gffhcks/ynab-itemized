"""Amazon Request My Data integration."""

import csv
import decimal
import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from ynab_itemized.models.transaction import ItemizedTransaction, TransactionItem

from .base import StoreIntegration

logger = logging.getLogger(__name__)


class AmazonRequestMyDataIntegration(StoreIntegration):
    """Integration for Amazon 'Request My Data' CSV exports."""

    # Required columns in Amazon CSV
    REQUIRED_COLUMNS = {
        "Order Date",
        "Order ID",
        "Title",
        "Purchase Price Per Unit",
        "Quantity",
        "Item Subtotal",
        "Item Subtotal Tax",
        "Item Total",
    }

    @property
    def store_name(self) -> str:
        """Return store name."""
        return "Amazon"

    @property
    def integration_type(self) -> str:
        """Return integration type."""
        return "csv"

    def get_supported_date_range(self) -> int:
        """
        Amazon Request My Data provides all order history.

        Returns:
            Very large number (10+ years)
        """
        return 3650  # 10 years

    def parse_data(self, raw_data: Any) -> List[ItemizedTransaction]:
        """
        Parse Amazon CSV file.

        Args:
            raw_data: Path to Amazon CSV file (string or Path)

        Returns:
            List of ItemizedTransaction objects
        """
        file_path = Path(raw_data)
        return self.parse_csv_file(file_path)

    def parse_csv_file(self, file_path: Path) -> List[ItemizedTransaction]:
        """
        Parse Amazon Request My Data CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            List of ItemizedTransaction objects grouped by order

        Raises:
            ValueError: If CSV is invalid or missing required columns
        """
        logger.info(f"Parsing Amazon CSV file: {file_path}")

        # Read CSV file
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate columns
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no headers")

            missing_columns = self.REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )

            # Read all rows
            rows = list(reader)

        if not rows:
            logger.warning("CSV file contains no data rows")
            return []

        # Group items by order ID
        grouped_orders = self._group_items_by_order(rows)

        # Parse each order into ItemizedTransaction
        transactions = []
        for order_id, order_items in grouped_orders.items():
            try:
                transaction = self._parse_order(order_id, order_items)
                transactions.append(transaction)
            except Exception as e:
                logger.error(f"Failed to parse order {order_id}: {e}")
                raise

        logger.info(f"Parsed {len(transactions)} transactions from {len(rows)} items")
        return transactions

    def _group_items_by_order(
        self, rows: List[Dict[str, str]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Group CSV rows by Order ID.

        Args:
            rows: List of CSV row dictionaries

        Returns:
            Dictionary mapping order ID to list of item rows
        """
        grouped = defaultdict(list)
        for row in rows:
            order_id = row.get("Order ID", "").strip()
            if order_id:
                grouped[order_id].append(row)
        return dict(grouped)

    def _parse_order(
        self, order_id: str, order_items: List[Dict[str, str]]
    ) -> ItemizedTransaction:
        """
        Parse a single order into ItemizedTransaction.

        Args:
            order_id: Amazon order ID
            order_items: List of item rows for this order

        Returns:
            ItemizedTransaction object

        Raises:
            ValueError: If data is invalid
        """
        if not order_items:
            raise ValueError(f"Order {order_id} has no items")

        # Get order-level data from first item
        first_item = order_items[0]

        # Parse order date
        order_date_str = first_item.get("Order Date", "").strip()
        try:
            # Amazon uses MM/DD/YYYY format
            order_date = datetime.strptime(order_date_str, "%m/%d/%Y").date()
        except ValueError:
            raise ValueError(
                f"Invalid date format for order {order_id}: {order_date_str}"
            )

        # Get merchant name (usually from Website column)
        merchant_name = first_item.get("Website", "Amazon.com").strip()
        if not merchant_name:
            merchant_name = "Amazon.com"

        # Parse items
        items = []
        total_amount = Decimal("0")
        total_tax = Decimal("0")

        for item_row in order_items:
            item, item_total, item_tax = self._parse_item(item_row, order_id)
            items.append(item)
            total_amount += item_total
            total_tax += item_tax

        # Create ItemizedTransaction
        transaction = ItemizedTransaction(
            transaction_date=order_date,
            total_amount=total_amount,
            merchant_name=merchant_name,
            items=items,
            source="amazon",
            source_transaction_id=order_id,
            total_tax=total_tax,
            metadata={
                "order_id": order_id,
                "import_source": "amazon_request_my_data",
            },
        )

        return transaction

    def _parse_item(
        self, item_row: Dict[str, str], order_id: str
    ) -> tuple[TransactionItem, Decimal, Decimal]:
        """
        Parse a single item row.

        Args:
            item_row: CSV row dictionary for item
            order_id: Order ID (for error messages)

        Returns:
            Tuple of (TransactionItem, item_total, item_tax)

        Raises:
            ValueError: If data is invalid
        """
        # Parse required fields
        title = item_row.get("Title", "").strip()
        if not title:
            raise ValueError(f"Item in order {order_id} has no title")

        # Parse amounts
        try:
            unit_price = Decimal(
                item_row.get("Purchase Price Per Unit", "0").strip().replace("$", "")
            )
            quantity = int(item_row.get("Quantity", "1").strip())
            item_subtotal = Decimal(
                item_row.get("Item Subtotal", "0").strip().replace("$", "")
            )
            item_tax = Decimal(
                item_row.get("Item Subtotal Tax", "0").strip().replace("$", "")
            )
            item_total = Decimal(
                item_row.get("Item Total", "0").strip().replace("$", "")
            )
        except (ValueError, decimal.InvalidOperation) as e:
            raise ValueError(f"Invalid amount in order {order_id}, item '{title}': {e}")

        # Parse optional fields
        category = item_row.get("Category", "").strip()
        asin = item_row.get("ASIN/ISBN", "").strip()
        seller = item_row.get("Seller", "").strip()
        condition = item_row.get("Condition", "").strip()

        # Create TransactionItem
        # Note: amount should be unit_price for single items, not subtotal
        # The subtotal is unit_price * quantity
        item = TransactionItem(
            name=title,
            amount=unit_price,
            quantity=quantity,
            unit_price=unit_price,
            tax_amount=item_tax,
            metadata={
                "asin": asin,
                "category": category,
                "seller": seller,
                "condition": condition,
                "order_id": order_id,
            },
        )

        return item, item_total, item_tax
