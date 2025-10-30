"""Base classes for store integrations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ynab_itemized.models.transaction import ItemizedTransaction


class StoreIntegration(ABC):
    """Abstract base class for store integrations."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with store-specific configuration.

        Args:
            config: Store-specific configuration dictionary
        """
        self.config = config

    @property
    @abstractmethod
    def store_name(self) -> str:
        """Return the store name (e.g., 'Amazon', 'Target')."""
        pass

    @property
    @abstractmethod
    def integration_type(self) -> str:
        """
        Return integration type.

        Returns:
            One of: 'api', 'csv', 'ocr', 'scraper', 'extension'
        """
        pass

    @abstractmethod
    def parse_data(self, raw_data: Any) -> List[ItemizedTransaction]:
        """
        Parse raw store data into ItemizedTransaction objects.

        Args:
            raw_data: Store-specific raw transaction data
                     (could be file path, API response, etc.)

        Returns:
            List of parsed ItemizedTransaction objects
        """
        pass

    def get_supported_date_range(self) -> int:
        """
        Return how many days back transactions are available.

        Returns:
            Number of days (default: 90)
        """
        return 90
