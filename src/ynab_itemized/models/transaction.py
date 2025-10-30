"""Transaction-related data models."""

from datetime import date as Date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from .base import BaseModel


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""

    CLEARED = "cleared"
    UNCLEARED = "uncleared"
    RECONCILED = "reconciled"


class TransactionItem(BaseModel):
    """Individual item within a transaction."""

    name: str = Field(..., description="Item name or description")
    amount: Decimal = Field(..., description="Item amount in account currency")
    quantity: Optional[int] = Field(default=1, description="Quantity of items")
    unit_price: Optional[Decimal] = Field(None, description="Price per unit")
    category: Optional[str] = Field(None, description="Item category")
    subcategory: Optional[str] = Field(None, description="Item subcategory")
    brand: Optional[str] = Field(None, description="Brand name")
    sku: Optional[str] = Field(None, description="Stock keeping unit")
    barcode: Optional[str] = Field(None, description="Product barcode")
    discount_amount: Optional[Decimal] = Field(
        default=Decimal("0"), description="Discount applied to this item"
    )
    tax_amount: Optional[Decimal] = Field(
        default=Decimal("0"), description="Tax amount for this item"
    )
    notes: Optional[str] = Field(None, description="Additional notes")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator(
        "amount", "unit_price", "discount_amount", "tax_amount", mode="before"
    )
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert numeric values to Decimal."""
        if v is None:
            return v
        return Decimal(str(v))

    @model_validator(mode="after")
    def calculate_unit_price(self):
        """Calculate unit price if not provided."""
        if self.unit_price is None:
            amount = self.amount
            quantity = self.quantity or 1
            if amount is not None and quantity > 0:
                self.unit_price = amount / Decimal(str(quantity))
        return self


class YNABSubtransaction(BaseModel):
    """YNAB subtransaction data (for split transactions)."""

    subtransaction_id: Optional[str] = Field(
        None, description="Subtransaction ID (null for new subtransactions)"
    )
    amount: Decimal = Field(..., description="Amount in milliunits")
    memo: Optional[str] = Field(None, description="Subtransaction memo")
    payee_id: Optional[str] = Field(None, description="Payee ID")
    payee_name: Optional[str] = Field(None, description="Payee name")
    category_id: Optional[str] = Field(None, description="Category ID")
    category_name: Optional[str] = Field(None, description="Category name")
    transfer_account_id: Optional[str] = Field(
        None, description="Transfer account ID (if this is a transfer)"
    )
    transfer_transaction_id: Optional[str] = Field(
        None, description="Transfer transaction ID (if this is a transfer)"
    )
    deleted: bool = Field(
        default=False, description="Whether subtransaction is deleted"
    )

    @field_validator("amount", mode="before")
    @classmethod
    def convert_amount_to_decimal(cls, v):
        """Convert amount to Decimal."""
        return Decimal(str(v))


class YNABTransaction(BaseModel):
    """YNAB transaction data."""

    ynab_id: str = Field(..., description="YNAB transaction ID")
    account_id: str = Field(..., description="YNAB account ID")
    category_id: Optional[str] = Field(None, description="YNAB category ID")
    payee_name: Optional[str] = Field(None, description="Payee name")
    memo: Optional[str] = Field(None, description="Transaction memo")
    amount: Decimal = Field(..., description="Transaction amount in milliunits")
    date: Date = Field(..., description="Transaction date")
    cleared: TransactionStatus = Field(default=TransactionStatus.UNCLEARED)
    approved: bool = Field(default=True)
    flag_color: Optional[str] = Field(None, description="Flag color")
    import_id: Optional[str] = Field(None, description="Import ID")
    subtransactions: List["YNABSubtransaction"] = Field(
        default_factory=list,
        description="Subtransactions (for split transactions)",
    )

    @field_validator("amount", mode="before")
    @classmethod
    def convert_amount_to_decimal(cls, v):
        """Convert amount to Decimal."""
        return Decimal(str(v))

    @property
    def has_subtransactions(self) -> bool:
        """Check if transaction has subtransactions."""
        return len(self.subtransactions) > 0

    def validate_subtransaction_amounts(self) -> bool:
        """
        Validate that subtransaction amounts sum to transaction amount.

        Returns:
            True if valid, False otherwise
        """
        if not self.has_subtransactions:
            return True

        subtotal = sum(st.amount for st in self.subtransactions)
        return subtotal == self.amount

    def dict_for_db(self) -> Dict[str, Any]:
        """
        Return dictionary suitable for database storage.

        Excludes subtransactions field since they are stored separately.
        """
        data = super().dict_for_db()
        # Remove subtransactions - they're not stored in YNABTransactionDB
        data.pop("subtransactions", None)
        # Set has_subtransactions flag
        data["has_subtransactions"] = self.has_subtransactions
        return data


class ItemizedTransaction(BaseModel):
    """Complete itemized transaction with YNAB data and item details."""

    ynab_transaction: Optional[YNABTransaction] = Field(
        None, description="YNAB transaction data"
    )
    items: List[TransactionItem] = Field(
        default_factory=list, description="Itemized breakdown"
    )

    # Required fields for matching
    transaction_date: Optional[Date] = Field(
        None, description="Transaction date for matching"
    )
    total_amount: Optional[Decimal] = Field(
        None, description="Total transaction amount"
    )
    merchant_name: Optional[str] = Field(None, description="Merchant name for matching")

    # Matching metadata
    match_status: str = Field(default="unmatched", description="Match status")
    match_confidence: Optional[float] = Field(
        None, description="Match confidence score"
    )
    match_method: Optional[str] = Field(None, description="Method used for matching")
    match_notes: Optional[str] = Field(None, description="Notes about the match")

    # Source tracking
    source: Optional[str] = Field(None, description="Source of the transaction")
    source_transaction_id: Optional[str] = Field(
        None, description="Original transaction ID from source"
    )

    # Summary fields
    subtotal: Optional[Decimal] = Field(
        None, description="Subtotal before tax and discounts"
    )
    total_tax: Optional[Decimal] = Field(None, description="Total tax amount")
    total_discount: Optional[Decimal] = Field(None, description="Total discount amount")
    tip_amount: Optional[Decimal] = Field(
        default=Decimal("0"), description="Tip amount"
    )

    # Store/merchant information
    store_name: Optional[str] = Field(None, description="Store or merchant name")
    store_location: Optional[str] = Field(None, description="Store location")
    store_phone: Optional[str] = Field(None, description="Store phone number")
    receipt_number: Optional[str] = Field(None, description="Receipt number")

    # Additional metadata
    payment_method: Optional[str] = Field(None, description="Payment method used")
    cashier: Optional[str] = Field(None, description="Cashier name")
    register_number: Optional[str] = Field(None, description="Register number")
    receipt_image_path: Optional[str] = Field(None, description="Path to receipt image")
    notes: Optional[str] = Field(None, description="Additional notes")
    tags: List[str] = Field(default_factory=list, description="Custom tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator(
        "subtotal", "total_tax", "total_discount", "tip_amount", mode="before"
    )
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert numeric values to Decimal."""
        if v is None:
            return v
        return Decimal(str(v))

    @property
    def calculated_subtotal(self) -> Decimal:
        """Calculate subtotal from items."""
        return sum(item.amount for item in self.items) or Decimal("0")

    @property
    def calculated_tax(self) -> Decimal:
        """Calculate total tax from items."""
        tax_amounts = (item.tax_amount or Decimal("0") for item in self.items)
        return sum(tax_amounts) or Decimal("0")

    @property
    def calculated_discount(self) -> Decimal:
        """Calculate total discount from items."""
        discount_amounts = (item.discount_amount or Decimal("0") for item in self.items)
        return sum(discount_amounts) or Decimal("0")

    @property
    def calculated_total(self) -> Decimal:
        """Calculate total amount."""
        return (
            self.calculated_subtotal
            + self.calculated_tax
            - self.calculated_discount
            + (self.tip_amount or Decimal("0"))
        )

    def validate_totals(self) -> bool:
        """Validate that calculated totals match YNAB transaction amount."""
        if not self.ynab_transaction:
            # If no YNAB transaction, validate against total_amount if available
            if self.total_amount:
                calculated_total = self.calculated_total
                return abs(self.total_amount - calculated_total) < Decimal("0.01")
            return True  # Can't validate without reference amount

        # Convert YNAB milliunits to regular units
        ynab_amount = abs(self.ynab_transaction.amount / 1000)
        calculated_total = self.calculated_total

        # Allow for small rounding differences
        return abs(ynab_amount - calculated_total) < Decimal("0.01")

    @field_validator("total_amount", mode="before")
    @classmethod
    def convert_total_amount_to_decimal(cls, v):
        """Convert total_amount to Decimal."""
        if v is None:
            return v
        return Decimal(str(v))

    @field_validator("match_confidence", mode="before")
    @classmethod
    def validate_match_confidence(cls, v):
        """Validate match confidence is between 0 and 1."""
        if v is None:
            return v
        confidence = float(v)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Match confidence must be between 0.0 and 1.0")
        return confidence

    @field_validator("match_status")
    @classmethod
    def validate_match_status(cls, v):
        """Validate match status is one of the allowed values."""
        allowed_statuses = {"unmatched", "matched", "manual_match", "no_match"}
        if v not in allowed_statuses:
            raise ValueError(f"Match status must be one of: {allowed_statuses}")
        return v
