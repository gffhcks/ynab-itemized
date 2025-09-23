"""Transaction-related data models."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import Field, validator

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
    discount_amount: Optional[Decimal] = Field(default=Decimal("0"), description="Discount applied to this item")
    tax_amount: Optional[Decimal] = Field(default=Decimal("0"), description="Tax amount for this item")
    notes: Optional[str] = Field(None, description="Additional notes")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('amount', 'unit_price', 'discount_amount', 'tax_amount', pre=True)
    def convert_to_decimal(cls, v):
        """Convert numeric values to Decimal."""
        if v is None:
            return v
        return Decimal(str(v))
    
    @validator('unit_price', always=True)
    def calculate_unit_price(cls, v, values):
        """Calculate unit price if not provided."""
        if v is None and 'amount' in values and 'quantity' in values:
            quantity = values['quantity'] or 1
            if quantity > 0:
                return values['amount'] / Decimal(str(quantity))
        return v


class YNABTransaction(BaseModel):
    """YNAB transaction data."""
    
    ynab_id: str = Field(..., description="YNAB transaction ID")
    account_id: str = Field(..., description="YNAB account ID")
    category_id: Optional[str] = Field(None, description="YNAB category ID")
    payee_name: Optional[str] = Field(None, description="Payee name")
    memo: Optional[str] = Field(None, description="Transaction memo")
    amount: Decimal = Field(..., description="Transaction amount in milliunits")
    date: date = Field(..., description="Transaction date")
    cleared: TransactionStatus = Field(default=TransactionStatus.UNCLEARED)
    approved: bool = Field(default=True)
    flag_color: Optional[str] = Field(None, description="Flag color")
    import_id: Optional[str] = Field(None, description="Import ID")
    
    @validator('amount', pre=True)
    def convert_amount_to_decimal(cls, v):
        """Convert amount to Decimal."""
        return Decimal(str(v))


class ItemizedTransaction(BaseModel):
    """Complete itemized transaction with YNAB data and item details."""
    
    ynab_transaction: YNABTransaction = Field(..., description="YNAB transaction data")
    items: List[TransactionItem] = Field(default_factory=list, description="Itemized breakdown")
    
    # Summary fields
    subtotal: Optional[Decimal] = Field(None, description="Subtotal before tax and discounts")
    total_tax: Optional[Decimal] = Field(None, description="Total tax amount")
    total_discount: Optional[Decimal] = Field(None, description="Total discount amount")
    tip_amount: Optional[Decimal] = Field(default=Decimal("0"), description="Tip amount")
    
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
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('subtotal', 'total_tax', 'total_discount', 'tip_amount', pre=True)
    def convert_to_decimal(cls, v):
        """Convert numeric values to Decimal."""
        if v is None:
            return v
        return Decimal(str(v))
    
    @property
    def calculated_subtotal(self) -> Decimal:
        """Calculate subtotal from items."""
        return sum(item.amount for item in self.items)
    
    @property
    def calculated_tax(self) -> Decimal:
        """Calculate total tax from items."""
        return sum(item.tax_amount or Decimal("0") for item in self.items)
    
    @property
    def calculated_discount(self) -> Decimal:
        """Calculate total discount from items."""
        return sum(item.discount_amount or Decimal("0") for item in self.items)
    
    @property
    def calculated_total(self) -> Decimal:
        """Calculate total amount."""
        return (self.calculated_subtotal + 
                self.calculated_tax - 
                self.calculated_discount + 
                (self.tip_amount or Decimal("0")))
    
    def validate_totals(self) -> bool:
        """Validate that calculated totals match YNAB transaction amount."""
        # Convert YNAB milliunits to regular units
        ynab_amount = abs(self.ynab_transaction.amount / 1000)
        calculated_total = self.calculated_total
        
        # Allow for small rounding differences
        return abs(ynab_amount - calculated_total) < Decimal("0.01")
