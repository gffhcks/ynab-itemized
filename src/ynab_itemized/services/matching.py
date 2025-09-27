"""Transaction matching service."""

# mypy: disable-error-code="assignment,attr-defined"

from datetime import timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..database.models import (
    ItemizedTransactionDB,
    TransactionMatchDB,
    YNABTransactionDB,
)


class TransactionMatcher:
    """Service for matching YNAB transactions with itemized transactions."""

    def __init__(self, db_session: Session):
        """Initialize the matcher with a database session."""
        self.db = db_session

    def find_matches(
        self,
        itemized_transaction: ItemizedTransactionDB,
        date_tolerance_days: int = 3,
        amount_tolerance_percent: float = 0.05,
    ) -> List[Tuple[YNABTransactionDB, float]]:
        """
        Find potential YNAB transaction matches for an itemized transaction.

        Args:
            itemized_transaction: The itemized transaction to match
            date_tolerance_days: Number of days +/- to search for matches
            amount_tolerance_percent: Percentage tolerance for amount matching

        Returns:
            List of (ynab_transaction, match_score) tuples, sorted by score descending
        """
        matches = []

        # Calculate date range
        start_date = itemized_transaction.transaction_date - timedelta(
            days=date_tolerance_days
        )
        end_date = itemized_transaction.transaction_date + timedelta(
            days=date_tolerance_days
        )

        # Calculate amount range
        amount = abs(itemized_transaction.total_amount)
        amount_tolerance = amount * Decimal(str(amount_tolerance_percent))
        min_amount = -(
            amount + amount_tolerance
        )  # YNAB amounts are negative for expenses
        max_amount = -(amount - amount_tolerance)

        # Query for potential matches
        candidates = (
            self.db.query(YNABTransactionDB)
            .filter(
                and_(
                    YNABTransactionDB.date >= start_date,
                    YNABTransactionDB.date <= end_date,
                    YNABTransactionDB.amount >= min_amount,
                    YNABTransactionDB.amount <= max_amount,
                )
            )
            .all()
        )

        # Score each candidate
        for candidate in candidates:
            score = self._calculate_match_score(itemized_transaction, candidate)
            if score > 0.3:  # Only include matches with reasonable confidence
                matches.append((candidate, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _calculate_match_score(
        self, itemized: ItemizedTransactionDB, ynab: YNABTransactionDB
    ) -> float:
        """Calculate a match score between 0.0 and 1.0."""
        score = 0.0

        # Date proximity (30% weight)
        date_diff = abs((itemized.transaction_date - ynab.date).days)
        if date_diff == 0:
            score += 0.3
        elif date_diff <= 1:
            score += 0.25
        elif date_diff <= 3:
            score += 0.15
        elif date_diff <= 7:
            score += 0.05

        # Amount match (40% weight)
        itemized_amount = abs(itemized.total_amount)
        ynab_amount = abs(ynab.amount)
        amount_diff = abs(itemized_amount - ynab_amount)
        amount_ratio = amount_diff / max(itemized_amount, ynab_amount)

        if amount_ratio == 0:
            score += 0.4
        elif amount_ratio <= 0.01:  # 1% difference
            score += 0.35
        elif amount_ratio <= 0.05:  # 5% difference
            score += 0.25
        elif amount_ratio <= 0.10:  # 10% difference
            score += 0.15

        # Payee/merchant similarity (30% weight)
        if itemized.merchant_name and ynab.payee_name:
            similarity = SequenceMatcher(
                None, itemized.merchant_name.lower(), ynab.payee_name.lower()
            ).ratio()
            score += similarity * 0.3

        return min(score, 1.0)

    def create_match(
        self,
        ynab_transaction: YNABTransactionDB,
        itemized_transaction: ItemizedTransactionDB,
        match_score: float,
        match_method: str = "automatic",
        reviewed_by: Optional[str] = None,
    ) -> TransactionMatchDB:
        """Create a transaction match record."""
        match = TransactionMatchDB(
            id=f"match_{ynab_transaction.id}_{itemized_transaction.id}",
            ynab_transaction_id=ynab_transaction.id,
            itemized_transaction_id=itemized_transaction.id,
            match_score=match_score,
            match_method=match_method,
            status="candidate" if not reviewed_by else "accepted",
            reviewed_by=reviewed_by,
        )

        self.db.add(match)
        return match

    def accept_match(self, match: TransactionMatchDB, reviewed_by: str) -> None:
        """Accept a transaction match."""
        match.status = "accepted"
        match.reviewed_by = reviewed_by

        # Update the itemized transaction
        itemized = match.itemized_transaction
        itemized.ynab_transaction_id = match.ynab_transaction_id
        itemized.match_status = "matched"
        itemized.match_confidence = match.match_score
        itemized.match_method = match.match_method

    def reject_match(self, match: TransactionMatchDB, reviewed_by: str) -> None:
        """Reject a transaction match."""
        match.status = "rejected"
        match.reviewed_by = reviewed_by

    def get_unmatched_itemized_transactions(self) -> List[ItemizedTransactionDB]:
        """Get all unmatched itemized transactions."""
        return (
            self.db.query(ItemizedTransactionDB)
            .filter(ItemizedTransactionDB.match_status == "unmatched")
            .all()
        )

    def get_unmatched_ynab_transactions(self) -> List[YNABTransactionDB]:
        """Get YNAB transactions that don't have any accepted matches."""
        matched_ynab_ids = (
            self.db.query(TransactionMatchDB.ynab_transaction_id)
            .filter(TransactionMatchDB.status == "accepted")
            .subquery()
        )

        return (
            self.db.query(YNABTransactionDB)
            .filter(~YNABTransactionDB.id.in_(matched_ynab_ids))
            .all()
        )

    def auto_match_transactions(
        self, confidence_threshold: float = 0.8
    ) -> List[TransactionMatchDB]:
        """Automatically match transactions above confidence threshold."""
        auto_matches = []
        unmatched = self.get_unmatched_itemized_transactions()

        for itemized in unmatched:
            matches = self.find_matches(itemized)
            if matches and matches[0][1] >= confidence_threshold:
                # Auto-accept high-confidence matches
                ynab_transaction, score = matches[0]
                match = self.create_match(
                    ynab_transaction, itemized, score, "automatic"
                )
                self.accept_match(match, "system")
                auto_matches.append(match)

        self.db.commit()
        return auto_matches
