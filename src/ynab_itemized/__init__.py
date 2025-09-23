"""YNAB Itemized Transaction Manager.

A Python package for managing itemized transaction data with YNAB integration.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .ynab.client import YNABClient
from .models.transaction import ItemizedTransaction, TransactionItem
from .database.manager import DatabaseManager

__all__ = [
    "YNABClient",
    "ItemizedTransaction", 
    "TransactionItem",
    "DatabaseManager",
]
