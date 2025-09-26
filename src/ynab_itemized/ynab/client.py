"""YNAB API client."""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import get_settings
from ..models.transaction import TransactionStatus, YNABTransaction
from .exceptions import (
    YNABAPIError,
    YNABAuthError,
    YNABNotFoundError,
    YNABRateLimitError,
    YNABValidationError,
)

logger = logging.getLogger(__name__)


class YNABClient:
    """Client for interacting with YNAB API."""

    def __init__(
        self, api_token: str = None, budget_id: str = None, base_url: str = None
    ):
        """Initialize YNAB client."""
        settings = get_settings()

        self.api_token = api_token or settings.ynab_api_token
        self.budget_id = budget_id or settings.ynab_budget_id
        self.base_url = base_url or settings.ynab_api_base_url

        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "ynab-itemized/0.1.0",
            }
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to YNAB API with error handling."""
        url = urljoin(self.base_url, endpoint)

        try:
            response = self.session.request(method, url, **kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise YNABRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    retry_after=retry_after,
                    status_code=response.status_code,
                )

            # Handle authentication errors
            if response.status_code == 401:
                raise YNABAuthError(
                    "Authentication failed. Check your API token.",
                    status_code=response.status_code,
                )

            # Handle not found errors
            if response.status_code == 404:
                raise YNABNotFoundError(
                    "Resource not found.", status_code=response.status_code
                )

            # Handle validation errors
            if response.status_code == 400:
                error_data = response.json() if response.content else {}
                error_info = error_data.get("error", {})
                error_detail = error_info.get("detail", "Unknown error")
                raise YNABValidationError(
                    f"Validation error: {error_detail}",
                    status_code=response.status_code,
                    response_data=error_data,
                )

            # Handle other client/server errors
            if not response.ok:
                error_data = response.json() if response.content else {}
                raise YNABAPIError(
                    f"API request failed: {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data,
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise YNABAPIError(f"Request failed: {e}")

    def get_budgets(self) -> List[Dict[str, Any]]:
        """Get list of budgets."""
        response = self._make_request("GET", "/budgets")
        return response["data"]["budgets"]

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get accounts for the configured budget."""
        response = self._make_request("GET", f"/budgets/{self.budget_id}/accounts")
        return response["data"]["accounts"]

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get categories for the configured budget."""
        response = self._make_request("GET", f"/budgets/{self.budget_id}/categories")
        return response["data"]["category_groups"]

    def get_transactions(
        self, account_id: str = None, since_date: date = None, type_filter: str = None
    ) -> List[YNABTransaction]:
        """Get transactions from YNAB."""
        endpoint = f"/budgets/{self.budget_id}/transactions"
        params = {}

        if since_date:
            params["since_date"] = since_date.isoformat()
        if type_filter:
            params["type"] = type_filter

        response = self._make_request("GET", endpoint, params=params)
        transactions = response["data"]["transactions"]

        # Filter by account if specified
        if account_id:
            transactions = [t for t in transactions if t["account_id"] == account_id]

        # Convert to our model
        ynab_transactions = []
        for t in transactions:
            try:
                transaction = YNABTransaction(
                    ynab_id=t["id"],
                    account_id=t["account_id"],
                    category_id=t["category_id"],
                    payee_name=t.get("payee_name"),
                    memo=t.get("memo"),
                    amount=t["amount"],
                    date=datetime.fromisoformat(t["date"]).date(),
                    cleared=TransactionStatus(t["cleared"]),
                    approved=t["approved"],
                    flag_color=t.get("flag_color"),
                    import_id=t.get("import_id"),
                )
                ynab_transactions.append(transaction)
            except Exception as e:
                logger.warning(
                    f"Failed to parse transaction {t.get('id', 'unknown')}: {e}"
                )
                continue

        return ynab_transactions

    def get_transaction(self, transaction_id: str) -> Optional[YNABTransaction]:
        """Get a specific transaction by ID."""
        try:
            response = self._make_request(
                "GET", f"/budgets/{self.budget_id}/transactions/{transaction_id}"
            )
            t = response["data"]["transaction"]

            return YNABTransaction(
                ynab_id=t["id"],
                account_id=t["account_id"],
                category_id=t["category_id"],
                payee_name=t.get("payee_name"),
                memo=t.get("memo"),
                amount=t["amount"],
                date=datetime.fromisoformat(t["date"]).date(),
                cleared=TransactionStatus(t["cleared"]),
                approved=t["approved"],
                flag_color=t.get("flag_color"),
                import_id=t.get("import_id"),
            )
        except YNABNotFoundError:
            return None

    def update_transaction(self, transaction: YNABTransaction) -> YNABTransaction:
        """Update a transaction in YNAB."""
        transaction_data = {
            "account_id": transaction.account_id,
            "category_id": transaction.category_id,
            "payee_name": transaction.payee_name,
            "memo": transaction.memo,
            "amount": int(transaction.amount),
            "date": transaction.date.isoformat(),
            "cleared": transaction.cleared.value,
            "approved": transaction.approved,
            "flag_color": transaction.flag_color,
        }

        # Remove None values
        transaction_data = {k: v for k, v in transaction_data.items() if v is not None}

        response = self._make_request(
            "PATCH",
            f"/budgets/{self.budget_id}/transactions/{transaction.ynab_id}",
            json={"transaction": transaction_data},
        )

        t = response["data"]["transaction"]
        return YNABTransaction(
            ynab_id=t["id"],
            account_id=t["account_id"],
            category_id=t["category_id"],
            payee_name=t.get("payee_name"),
            memo=t.get("memo"),
            amount=t["amount"],
            date=datetime.fromisoformat(t["date"]).date(),
            cleared=TransactionStatus(t["cleared"]),
            approved=t["approved"],
            flag_color=t.get("flag_color"),
            import_id=t.get("import_id"),
        )
