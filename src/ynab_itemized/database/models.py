"""SQLAlchemy database models."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class YNABTransactionDB(Base):  # type: ignore[valid-type,misc]
    """YNAB transaction database model."""

    __tablename__ = "ynab_transactions"

    id = Column(String, primary_key=True)
    ynab_id = Column(String, unique=True, nullable=False, index=True)
    account_id = Column(String, nullable=False)
    category_id = Column(String, nullable=True)
    payee_name = Column(String, nullable=True)
    memo = Column(Text, nullable=True)
    amount = Column(Numeric(precision=15, scale=3), nullable=False)
    date = Column(Date, nullable=False)
    cleared = Column(String, nullable=False, default="uncleared")
    approved = Column(Boolean, nullable=False, default=True)
    flag_color = Column(String, nullable=True)
    import_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationship to itemized transaction
    itemized_transaction = relationship(
        "ItemizedTransactionDB", back_populates="ynab_transaction", uselist=False
    )


class ItemizedTransactionDB(Base):  # type: ignore[valid-type,misc]
    """Itemized transaction database model."""

    __tablename__ = "itemized_transactions"

    id = Column(String, primary_key=True)
    ynab_transaction_id = Column(
        String, ForeignKey("ynab_transactions.id"), nullable=False
    )

    # Summary fields
    subtotal = Column(Numeric(precision=10, scale=2), nullable=True)
    total_tax = Column(Numeric(precision=10, scale=2), nullable=True)
    total_discount = Column(Numeric(precision=10, scale=2), nullable=True)
    tip_amount = Column(Numeric(precision=10, scale=2), default=0)

    # Store information
    store_name = Column(String, nullable=True)
    store_location = Column(String, nullable=True)
    store_phone = Column(String, nullable=True)
    receipt_number = Column(String, nullable=True)

    # Additional metadata
    payment_method = Column(String, nullable=True)
    cashier = Column(String, nullable=True)
    register_number = Column(String, nullable=True)
    receipt_image_path = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Store as JSON array
    extra_metadata = Column(JSON, nullable=True)  # Store as JSON object

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    ynab_transaction = relationship(
        "YNABTransactionDB", back_populates="itemized_transaction"
    )
    items = relationship(
        "TransactionItemDB", back_populates="transaction", cascade="all, delete-orphan"
    )


class TransactionItemDB(Base):  # type: ignore[valid-type,misc]
    """Transaction item database model."""

    __tablename__ = "transaction_items"

    id = Column(String, primary_key=True)
    transaction_id = Column(
        String, ForeignKey("itemized_transactions.id"), nullable=False
    )

    name = Column(String, nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(precision=10, scale=2), nullable=True)
    category = Column(String, nullable=True)
    subcategory = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    barcode = Column(String, nullable=True)
    discount_amount = Column(Numeric(precision=10, scale=2), default=0)
    tax_amount = Column(Numeric(precision=10, scale=2), default=0)
    notes = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationship
    transaction = relationship("ItemizedTransactionDB", back_populates="items")
