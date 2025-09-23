"""Database manager for YNAB Itemized."""

import logging
from contextlib import contextmanager
from typing import List, Optional, Generator

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_settings
from ..models.transaction import ItemizedTransaction, YNABTransaction, TransactionItem
from .models import Base, ItemizedTransactionDB, YNABTransactionDB, TransactionItemDB

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for YNAB Itemized."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager."""
        if database_url is None:
            settings = get_settings()
            database_url = settings.database_url
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
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
    
    def save_ynab_transaction(self, transaction: YNABTransaction) -> YNABTransactionDB:
        """Save YNAB transaction to database."""
        with self.get_session() as session:
            # Check if transaction already exists
            existing = session.query(YNABTransactionDB).filter(
                YNABTransactionDB.ynab_id == transaction.ynab_id
            ).first()
            
            if existing:
                # Update existing transaction
                for key, value in transaction.dict().items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.update_timestamp()
                return existing
            else:
                # Create new transaction
                db_transaction = YNABTransactionDB(**transaction.dict_for_db())
                session.add(db_transaction)
                session.flush()
                return db_transaction
    
    def save_itemized_transaction(self, itemized: ItemizedTransaction) -> ItemizedTransactionDB:
        """Save complete itemized transaction to database."""
        with self.get_session() as session:
            # First save the YNAB transaction
            ynab_db = self.save_ynab_transaction(itemized.ynab_transaction)
            
            # Check if itemized transaction already exists
            existing = session.query(ItemizedTransactionDB).filter(
                ItemizedTransactionDB.ynab_transaction_id == ynab_db.id
            ).first()
            
            if existing:
                # Update existing itemized transaction
                itemized_data = itemized.dict(exclude={'ynab_transaction', 'items'})
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
                itemized_data = itemized.dict(exclude={'ynab_transaction', 'items'})
                itemized_data['ynab_transaction_id'] = ynab_db.id
                db_itemized = ItemizedTransactionDB(**itemized_data)
                session.add(db_itemized)
                session.flush()
            
            # Add items
            for item in itemized.items:
                item_data = item.dict_for_db()
                item_data['transaction_id'] = db_itemized.id
                db_item = TransactionItemDB(**item_data)
                session.add(db_item)
            
            return db_itemized
    
    def get_itemized_transaction(self, ynab_id: str) -> Optional[ItemizedTransaction]:
        """Get itemized transaction by YNAB ID."""
        with self.get_session() as session:
            result = session.query(ItemizedTransactionDB).join(YNABTransactionDB).filter(
                YNABTransactionDB.ynab_id == ynab_id
            ).first()
            
            if not result:
                return None
            
            return self._db_to_model(result)
    
    def get_all_itemized_transactions(self) -> List[ItemizedTransaction]:
        """Get all itemized transactions."""
        with self.get_session() as session:
            results = session.query(ItemizedTransactionDB).all()
            return [self._db_to_model(result) for result in results]
    
    def delete_itemized_transaction(self, ynab_id: str) -> bool:
        """Delete itemized transaction by YNAB ID."""
        with self.get_session() as session:
            result = session.query(ItemizedTransactionDB).join(YNABTransactionDB).filter(
                YNABTransactionDB.ynab_id == ynab_id
            ).first()
            
            if result:
                session.delete(result)
                return True
            return False
    
    def _db_to_model(self, db_itemized: ItemizedTransactionDB) -> ItemizedTransaction:
        """Convert database model to Pydantic model."""
        # Convert YNAB transaction
        ynab_data = {
            'ynab_id': db_itemized.ynab_transaction.ynab_id,
            'account_id': db_itemized.ynab_transaction.account_id,
            'category_id': db_itemized.ynab_transaction.category_id,
            'payee_name': db_itemized.ynab_transaction.payee_name,
            'memo': db_itemized.ynab_transaction.memo,
            'amount': db_itemized.ynab_transaction.amount,
            'date': db_itemized.ynab_transaction.date,
            'cleared': db_itemized.ynab_transaction.cleared,
            'approved': db_itemized.ynab_transaction.approved,
            'flag_color': db_itemized.ynab_transaction.flag_color,
            'import_id': db_itemized.ynab_transaction.import_id,
        }
        ynab_transaction = YNABTransaction(**ynab_data)
        
        # Convert items
        items = []
        for db_item in db_itemized.items:
            item_data = {
                'name': db_item.name,
                'amount': db_item.amount,
                'quantity': db_item.quantity,
                'unit_price': db_item.unit_price,
                'category': db_item.category,
                'subcategory': db_item.subcategory,
                'brand': db_item.brand,
                'sku': db_item.sku,
                'barcode': db_item.barcode,
                'discount_amount': db_item.discount_amount,
                'tax_amount': db_item.tax_amount,
                'notes': db_item.notes,
                'metadata': db_item.metadata or {},
            }
            items.append(TransactionItem(**item_data))
        
        # Convert itemized transaction
        itemized_data = {
            'ynab_transaction': ynab_transaction,
            'items': items,
            'subtotal': db_itemized.subtotal,
            'total_tax': db_itemized.total_tax,
            'total_discount': db_itemized.total_discount,
            'tip_amount': db_itemized.tip_amount,
            'store_name': db_itemized.store_name,
            'store_location': db_itemized.store_location,
            'store_phone': db_itemized.store_phone,
            'receipt_number': db_itemized.receipt_number,
            'payment_method': db_itemized.payment_method,
            'cashier': db_itemized.cashier,
            'register_number': db_itemized.register_number,
            'receipt_image_path': db_itemized.receipt_image_path,
            'notes': db_itemized.notes,
            'tags': db_itemized.tags or [],
            'metadata': db_itemized.metadata or {},
        }
        
        return ItemizedTransaction(**itemized_data)
