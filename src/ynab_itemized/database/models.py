"""SQLAlchemy database models."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
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
    has_subtransactions = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationship to itemized transactions
    # (one YNAB transaction can match multiple itemized transactions)
    itemized_transactions = relationship(
        "ItemizedTransactionDB", back_populates="ynab_transaction"
    )


class ItemizedTransactionDB(Base):  # type: ignore[valid-type,misc]
    """Itemized transaction database model."""

    __tablename__ = "itemized_transactions"

    id = Column(String, primary_key=True)

    # Make YNAB transaction optional to support unmatched itemized transactions
    ynab_transaction_id = Column(
        String, ForeignKey("ynab_transactions.id"), nullable=True
    )

    # Add fields needed for matching
    transaction_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(precision=15, scale=3), nullable=False)
    merchant_name = Column(String, nullable=True)  # For matching with YNAB payee

    # Matching status and metadata
    match_status = Column(
        String, nullable=False, default="unmatched"
    )  # unmatched, matched, manual_match, no_match
    match_confidence = Column(
        Numeric(precision=3, scale=2), nullable=True
    )  # 0.0 to 1.0
    match_method = Column(String, nullable=True)  # exact, fuzzy, manual
    match_notes = Column(Text, nullable=True)

    # Source information
    source = Column(String, nullable=False)  # e.g., "amazon", "target", "manual"
    source_transaction_id = Column(
        String, nullable=True
    )  # Original merchant transaction ID

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

    # Subtransaction sync tracking
    subtransactions_synced_at = Column(
        DateTime, nullable=True
    )  # Last time subtransactions were synced to YNAB

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    ynab_transaction = relationship(
        "YNABTransactionDB", back_populates="itemized_transactions"
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

    # YNAB subtransaction mapping
    ynab_subtransaction_id = Column(
        String, nullable=True, index=True
    )  # Maps to YNAB subtransaction ID
    ynab_category_id = Column(
        String, nullable=True
    )  # YNAB category ID from subtransaction

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


class TransactionMatchDB(Base):  # type: ignore[valid-type,misc]
    """Transaction matching attempts and results."""

    __tablename__ = "transaction_matches"

    id = Column(String, primary_key=True)
    ynab_transaction_id = Column(
        String, ForeignKey("ynab_transactions.id"), nullable=False
    )
    itemized_transaction_id = Column(
        String, ForeignKey("itemized_transactions.id"), nullable=False
    )

    # Match details
    match_score = Column(Numeric(precision=3, scale=2), nullable=False)  # 0.0 to 1.0
    match_method = Column(
        String, nullable=False
    )  # exact, date_amount, fuzzy_payee, manual
    match_criteria = Column(JSON, nullable=True)  # Store matching criteria used

    # Match status
    status = Column(
        String, nullable=False, default="candidate"
    )  # candidate, accepted, rejected
    reviewed_by = Column(String, nullable=True)  # User who reviewed the match
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ynab_transaction = relationship("YNABTransactionDB")
    itemized_transaction = relationship("ItemizedTransactionDB")


# Add indexes for efficient matching queries
Index("idx_ynab_date_amount", YNABTransactionDB.date, YNABTransactionDB.amount)
Index(
    "idx_itemized_date_amount",
    ItemizedTransactionDB.transaction_date,
    ItemizedTransactionDB.total_amount,
)
Index("idx_itemized_match_status", ItemizedTransactionDB.match_status)
Index("idx_match_status", TransactionMatchDB.status)
