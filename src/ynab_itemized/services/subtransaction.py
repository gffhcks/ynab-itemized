"""Service for managing YNAB subtransactions."""

import logging
from decimal import Decimal
from typing import List, Optional

from ..database.manager import DatabaseManager
from ..models.transaction import (
    ItemizedTransaction,
    YNABSubtransaction,
    YNABTransaction,
)
from ..ynab.client import YNABClient

logger = logging.getLogger(__name__)


class SubtransactionService:
    """Service for managing YNAB subtransactions."""

    def __init__(self, ynab_client: YNABClient, db_manager: DatabaseManager):
        """
        Initialize the service.

        Args:
            ynab_client: YNAB API client
            db_manager: Database manager
        """
        self.ynab_client = ynab_client
        self.db_manager = db_manager

    def create_subtransactions_from_items(
        self,
        itemized_transaction: ItemizedTransaction,
        include_tax_subtransaction: bool = True,
        include_discount_subtransaction: bool = True,
    ) -> List[YNABSubtransaction]:
        """
        Convert transaction items to YNAB subtransactions.

        Args:
            itemized_transaction: The itemized transaction
            include_tax_subtransaction: Create separate tax subtransaction
            include_discount_subtransaction: Create separate discount subtransaction

        Returns:
            List of YNABSubtransaction objects

        Raises:
            ValueError: If subtransaction amounts don't sum to transaction total
        """
        subtransactions = []

        # Create subtransaction for each item
        for item in itemized_transaction.items:
            # Convert dollars to milliunits (multiply by 1000)
            amount_milliunits = int(item.amount * 1000)

            # Make amount negative for expenses (YNAB convention)
            amount_milliunits = -abs(amount_milliunits)

            subtx = YNABSubtransaction(
                amount=Decimal(str(amount_milliunits)),
                memo=item.name,
                category_id=None,  # User can categorize later
            )
            subtransactions.append(subtx)

        # Add tax subtransaction if requested and tax exists
        if include_tax_subtransaction and itemized_transaction.total_tax:
            tax_milliunits = -int(itemized_transaction.total_tax * 1000)
            subtransactions.append(
                YNABSubtransaction(
                    amount=Decimal(str(tax_milliunits)),
                    memo="Tax",
                    category_id=None,  # User can categorize later
                )
            )

        # Add discount subtransaction if requested and discount exists
        if include_discount_subtransaction and itemized_transaction.total_discount:
            # Discounts are positive (reduce the expense)
            discount_milliunits = int(itemized_transaction.total_discount * 1000)
            subtransactions.append(
                YNABSubtransaction(
                    amount=Decimal(str(discount_milliunits)),
                    memo="Discount",
                    category_id=None,
                )
            )

        # Validate that subtransactions sum to transaction total
        if itemized_transaction.total_amount:
            self._validate_subtransaction_amounts(
                subtransactions, itemized_transaction.total_amount
            )

        return subtransactions

    def _validate_subtransaction_amounts(
        self, subtransactions: List[YNABSubtransaction], expected_total: Decimal
    ) -> None:
        """
        Validate that subtransactions sum to expected total.

        Adjusts for small rounding errors (up to 1 cent).

        Args:
            subtransactions: List of subtransactions
            expected_total: Expected total amount in dollars

        Raises:
            ValueError: If amounts don't match and difference is > 1 cent
        """
        if not subtransactions:
            return

        subtx_sum = sum(st.amount for st in subtransactions)
        expected_milliunits = -int(expected_total * 1000)

        if subtx_sum != expected_milliunits:
            diff = abs(subtx_sum - expected_milliunits)
            logger.warning(
                f"Subtransaction sum ({subtx_sum}) doesn't match "
                f"expected total ({expected_milliunits}). Difference: {diff} milliunits"
            )

            # If difference is small (rounding error), adjust last subtransaction
            if diff <= 10:  # 10 milliunits = 1 cent
                adjustment = expected_milliunits - subtx_sum
                subtransactions[-1].amount += adjustment
                logger.info(
                    f"Adjusted last subtransaction by {adjustment} milliunits for rounding"
                )
            else:
                raise ValueError(
                    f"Subtransaction amounts don't sum to transaction total. "
                    f"Difference: {diff} milliunits ({diff / 1000:.2f} dollars)"
                )

    def sync_subtransactions_to_ynab(
        self,
        transaction: YNABTransaction,
        dry_run: bool = False,
    ) -> Optional[YNABTransaction]:
        """
        Update YNAB transaction with subtransactions.

        Args:
            transaction: YNABTransaction with subtransactions to sync
            dry_run: If True, don't actually update YNAB

        Returns:
            Updated YNABTransaction or None if dry_run
        """
        if dry_run:
            logger.info(
                f"DRY RUN: Would create {len(transaction.subtransactions)} subtransactions "
                f"for transaction {transaction.ynab_id}"
            )
            return None

        logger.info(
            f"Creating {len(transaction.subtransactions)} subtransactions "
            f"for transaction {transaction.ynab_id}"
        )

        updated_transaction = self.ynab_client.update_transaction_with_subtransactions(
            transaction
        )

        logger.info(f"Successfully created subtransactions for {transaction.ynab_id}")
        return updated_transaction
