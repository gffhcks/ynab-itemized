"""Validation utilities."""

from decimal import Decimal
from typing import List, Tuple

from ..models.transaction import ItemizedTransaction, TransactionItem


def validate_transaction_totals(
    transaction: ItemizedTransaction,
) -> Tuple[bool, List[str]]:
    """Validate that transaction totals are consistent."""
    errors = []

    # Check if items exist
    if not transaction.items:
        errors.append("Transaction has no items")
        return False, errors

    # Calculate totals from items
    calculated_subtotal = sum(item.amount for item in transaction.items)
    calculated_tax = sum(item.tax_amount or Decimal("0") for item in transaction.items)
    calculated_discount = sum(
        item.discount_amount or Decimal("0") for item in transaction.items
    )

    # Check subtotal
    if transaction.subtotal is not None:
        if abs(transaction.subtotal - calculated_subtotal) > Decimal("0.01"):
            errors.append(
                f"Subtotal mismatch: declared {transaction.subtotal}, "
                f"calculated {calculated_subtotal}"
            )

    # Check tax total
    if transaction.total_tax is not None:
        if abs(transaction.total_tax - calculated_tax) > Decimal("0.01"):
            errors.append(
                f"Tax total mismatch: declared {transaction.total_tax}, "
                f"calculated {calculated_tax}"
            )

    # Check discount total
    if transaction.total_discount is not None:
        if abs(transaction.total_discount - calculated_discount) > Decimal("0.01"):
            errors.append(
                f"Discount total mismatch: declared {transaction.total_discount}, "
                f"calculated {calculated_discount}"
            )

    # Check against YNAB transaction amount
    ynab_amount = abs(
        transaction.ynab_transaction.amount / 1000
    )  # Convert from milliunits
    calculated_total = (
        calculated_subtotal
        + calculated_tax
        - calculated_discount
        + (transaction.tip_amount or Decimal("0"))
    )

    if abs(ynab_amount - calculated_total) > Decimal("0.01"):
        errors.append(
            f"Total amount mismatch with YNAB: YNAB {ynab_amount}, "
            f"calculated {calculated_total}"
        )

    return len(errors) == 0, errors


def validate_item(item: TransactionItem) -> Tuple[bool, List[str]]:
    """Validate a single transaction item."""
    errors = []

    # Check required fields
    if not item.name or not item.name.strip():
        errors.append("Item name is required")

    if item.amount <= 0:
        errors.append("Item amount must be positive")

    # Check quantity and unit price consistency
    if item.quantity and item.unit_price:
        expected_amount = item.quantity * item.unit_price
        if abs(item.amount - expected_amount) > Decimal("0.01"):
            errors.append(
                f"Amount inconsistent with quantity × unit price: "
                f"{item.amount} ≠ {item.quantity} × {item.unit_price}"
            )

    # Check that discount and tax are not negative
    if item.discount_amount and item.discount_amount < 0:
        errors.append("Discount amount cannot be negative")

    if item.tax_amount and item.tax_amount < 0:
        errors.append("Tax amount cannot be negative")

    return len(errors) == 0, errors
