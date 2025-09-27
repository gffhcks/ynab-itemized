"""Database manager for YNAB Itemized."""

# mypy: disable-error-code="arg-type"

import logging
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Generator, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from ..models.transaction import ItemizedTransaction, TransactionItem, YNABTransaction
from .models import Base, ItemizedTransactionDB, TransactionItemDB, YNABTransactionDB

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for YNAB Itemized."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager."""
        if database_url is None:
            settings = get_settings()
            database_url = settings.database_url

        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_ynab_transaction(
        self, transaction: YNABTransaction, session=None
    ) -> YNABTransactionDB:
        """Save YNAB transaction to database."""
        if session is None:
            with self.get_session() as session:
                result = self._save_ynab_transaction_in_session(transaction, session)
                session.flush()
                session.refresh(result)
                # Expunge the object to make it safe to access outside the session
                session.expunge(result)
                return result
        else:
            return self._save_ynab_transaction_in_session(transaction, session)

    def _save_ynab_transaction_in_session(
        self, transaction: YNABTransaction, session
    ) -> YNABTransactionDB:
        """Internal method to save YNAB transaction within a session."""
        # Check if transaction already exists
        existing = (
            session.query(YNABTransactionDB)
            .filter(YNABTransactionDB.ynab_id == transaction.ynab_id)
            .first()
        )

        if existing:
            # Update existing transaction
            for key, value in transaction.dict_for_db().items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.update_timestamp()
            session.flush()
            return existing
        else:
            # Create new transaction
            db_transaction = YNABTransactionDB(**transaction.dict_for_db())
            session.add(db_transaction)
            session.flush()
            return db_transaction

    def save_itemized_transaction(
        self, itemized: ItemizedTransaction
    ) -> ItemizedTransactionDB:
        """Save complete itemized transaction to database."""
        with self.get_session() as session:
            ynab_db = None

            # Save YNAB transaction if it exists
            if itemized.ynab_transaction:
                ynab_db = self.save_ynab_transaction(itemized.ynab_transaction, session)

            # Check if itemized transaction already exists by ID
            existing = None
            if itemized.id:
                existing = (
                    session.query(ItemizedTransactionDB)
                    .filter(ItemizedTransactionDB.id == itemized.id)
                    .first()
                )

            if existing:
                # Update existing itemized transaction
                itemized_data = itemized.model_dump(
                    exclude={"ynab_transaction", "items"}
                )
                # Set the YNAB transaction ID if we have one
                if ynab_db:
                    itemized_data["ynab_transaction_id"] = ynab_db.id

                for key, value in itemized_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.update_timestamp()

                # Remove existing items and add new ones
                session.query(TransactionItemDB).filter(
                    TransactionItemDB.transaction_id == existing.id
                ).delete()

                db_itemized = existing
            else:
                # Create new itemized transaction
                itemized_data = itemized.model_dump(
                    exclude={"ynab_transaction", "items"}
                )
                # Set the YNAB transaction ID if we have one
                if ynab_db:
                    itemized_data["ynab_transaction_id"] = ynab_db.id
                else:
                    itemized_data["ynab_transaction_id"] = None

                # Ensure required fields are present
                if (
                    "transaction_date" not in itemized_data
                    or itemized_data["transaction_date"] is None
                ):
                    # Use created_at date as fallback
                    itemized_data["transaction_date"] = itemized.created_at.date()

                if (
                    "total_amount" not in itemized_data
                    or itemized_data["total_amount"] is None
                ):
                    # Calculate from items or use subtotal
                    total = itemized.calculated_subtotal
                    if itemized.total_tax:
                        total += itemized.total_tax
                    if itemized.tip_amount:
                        total += itemized.tip_amount
                    if itemized.total_discount:
                        total -= itemized.total_discount
                    itemized_data["total_amount"] = total

                # Set default values for new matching fields
                if itemized_data.get("match_status") is None:
                    itemized_data["match_status"] = "unmatched"
                if itemized_data.get("source") is None:
                    itemized_data["source"] = "manual"

                db_itemized = ItemizedTransactionDB(**itemized_data)
                session.add(db_itemized)
                session.flush()

            # Add items
            for item in itemized.items:
                item_data = item.dict_for_db()
                item_data["transaction_id"] = db_itemized.id
                db_item = TransactionItemDB(**item_data)
                session.add(db_item)

            session.flush()
            session.refresh(db_itemized)
            # Eagerly load the items relationship before expunging
            _ = db_itemized.items  # This triggers the lazy load
            # Expunge the object to make it safe to access outside the session
            session.expunge(db_itemized)
            return db_itemized

    def save_standalone_itemized_transaction(
        self,
        transaction_date: date,
        total_amount: Decimal,
        merchant_name: Optional[str] = None,
        source: str = "manual",
        items: Optional[List[TransactionItem]] = None,
        **kwargs,
    ) -> ItemizedTransactionDB:
        """Save an itemized transaction without a YNAB transaction."""
        from ..models.transaction import ItemizedTransaction

        # Create a minimal ItemizedTransaction object
        itemized_data = {
            "id": kwargs.get("id"),
            "created_at": datetime.now(),
            "ynab_transaction": None,
            "items": items or [],
            "transaction_date": transaction_date,
            "total_amount": total_amount,
            "merchant_name": merchant_name,
            "source": source,
            "match_status": "unmatched",
            **kwargs,
        }

        # Create ItemizedTransaction object
        itemized = ItemizedTransaction(**itemized_data)

        # Save using the main method
        return self.save_itemized_transaction(itemized)

    def get_itemized_transaction(
        self, transaction_id: str
    ) -> Optional[ItemizedTransaction]:
        """Get itemized transaction by ID."""
        with self.get_session() as session:
            result = (
                session.query(ItemizedTransactionDB)
                .filter(ItemizedTransactionDB.id == transaction_id)
                .first()
            )

            if not result:
                return None

            return self._db_to_model(result)

    def get_itemized_transaction_by_ynab_id(
        self, ynab_id: str
    ) -> Optional[ItemizedTransaction]:
        """Get itemized transaction by YNAB ID."""
        with self.get_session() as session:
            result = (
                session.query(ItemizedTransactionDB)
                .join(YNABTransactionDB)
                .filter(YNABTransactionDB.ynab_id == ynab_id)
                .first()
            )

            if not result:
                return None

            return self._db_to_model(result)

    def get_all_itemized_transactions(self) -> List[ItemizedTransaction]:
        """Get all itemized transactions."""
        with self.get_session() as session:
            results = session.query(ItemizedTransactionDB).all()
            return [self._db_to_model(result) for result in results]

    def delete_itemized_transaction(self, transaction_id: str) -> bool:
        """Delete itemized transaction by ID."""
        with self.get_session() as session:
            result = (
                session.query(ItemizedTransactionDB)
                .filter(ItemizedTransactionDB.id == transaction_id)
                .first()
            )

            if result:
                session.delete(result)
                return True
            return False

    def delete_itemized_transaction_by_ynab_id(self, ynab_id: str) -> bool:
        """Delete itemized transaction by YNAB ID."""
        with self.get_session() as session:
            result = (
                session.query(ItemizedTransactionDB)
                .join(YNABTransactionDB)
                .filter(YNABTransactionDB.ynab_id == ynab_id)
                .first()
            )

            if result:
                session.delete(result)
                return True
            return False

    def get_unmatched_itemized_transactions(self) -> List[ItemizedTransaction]:
        """Get all unmatched itemized transactions."""
        with self.get_session() as session:
            results = (
                session.query(ItemizedTransactionDB)
                .filter(ItemizedTransactionDB.match_status == "unmatched")
                .all()
            )
            return [self._db_to_model(result) for result in results]

    def get_itemized_transactions_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[ItemizedTransaction]:
        """Get itemized transactions within a date range."""
        with self.get_session() as session:
            results = (
                session.query(ItemizedTransactionDB)
                .filter(
                    ItemizedTransactionDB.transaction_date >= start_date,
                    ItemizedTransactionDB.transaction_date <= end_date,
                )
                .all()
            )
            return [self._db_to_model(result) for result in results]

    def _db_to_model(self, db_itemized: ItemizedTransactionDB) -> ItemizedTransaction:
        """Convert database model to Pydantic model."""
        # Convert YNAB transaction (if it exists)
        ynab_transaction = None
        if db_itemized.ynab_transaction:
            ynab_data = {
                "ynab_id": db_itemized.ynab_transaction.ynab_id,
                "account_id": db_itemized.ynab_transaction.account_id,
                "category_id": db_itemized.ynab_transaction.category_id,
                "payee_name": db_itemized.ynab_transaction.payee_name,
                "memo": db_itemized.ynab_transaction.memo,
                "amount": db_itemized.ynab_transaction.amount,
                "date": db_itemized.ynab_transaction.date,
                "cleared": db_itemized.ynab_transaction.cleared,
                "approved": db_itemized.ynab_transaction.approved,
                "flag_color": db_itemized.ynab_transaction.flag_color,
                "import_id": db_itemized.ynab_transaction.import_id,
            }
            ynab_transaction = YNABTransaction(**ynab_data)

        # Convert items
        items = []
        for db_item in db_itemized.items:
            item_data = {
                "name": db_item.name,
                "amount": db_item.amount,
                "quantity": db_item.quantity,
                "unit_price": db_item.unit_price,
                "category": db_item.category,
                "subcategory": db_item.subcategory,
                "brand": db_item.brand,
                "sku": db_item.sku,
                "barcode": db_item.barcode,
                "discount_amount": db_item.discount_amount,
                "tax_amount": db_item.tax_amount,
                "notes": db_item.notes,
                "metadata": db_item.extra_metadata or {},
            }
            items.append(TransactionItem(**item_data))

        # Convert itemized transaction
        return ItemizedTransaction(
            id=db_itemized.id,
            created_at=db_itemized.created_at,
            updated_at=db_itemized.updated_at,
            ynab_transaction=ynab_transaction,
            items=items,
            subtotal=db_itemized.subtotal,
            total_tax=db_itemized.total_tax,
            total_discount=db_itemized.total_discount,
            tip_amount=db_itemized.tip_amount,
            store_name=db_itemized.store_name,
            store_location=db_itemized.store_location,
            store_phone=db_itemized.store_phone,
            receipt_number=db_itemized.receipt_number,
            payment_method=db_itemized.payment_method,
            cashier=db_itemized.cashier,
            register_number=db_itemized.register_number,
            receipt_image_path=db_itemized.receipt_image_path,
            notes=db_itemized.notes,
            tags=db_itemized.tags or [],
            metadata=db_itemized.extra_metadata or {},
            # New matching fields
            transaction_date=db_itemized.transaction_date,
            total_amount=db_itemized.total_amount,
            merchant_name=db_itemized.merchant_name,
            match_status=db_itemized.match_status,
            match_confidence=db_itemized.match_confidence,
            match_method=db_itemized.match_method,
            match_notes=db_itemized.match_notes,
            source=db_itemized.source,
            source_transaction_id=db_itemized.source_transaction_id,
        )
