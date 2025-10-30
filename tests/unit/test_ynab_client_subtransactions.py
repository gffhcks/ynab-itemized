"""Test YNAB client subtransaction functionality."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from ynab_itemized.models.transaction import YNABSubtransaction, YNABTransaction
from ynab_itemized.ynab.client import YNABClient
from ynab_itemized.ynab.exceptions import YNABValidationError


@pytest.fixture
def mock_ynab_client():
    """Create a mock YNAB client."""
    with patch("ynab_itemized.ynab.client.requests") as mock_requests:
        client = YNABClient(api_token="test-token", budget_id="test-budget")
        client._make_request = MagicMock()
        yield client


class TestParseSubtransactions:
    """Test _parse_subtransactions method."""

    def test_parse_empty_subtransactions(self, mock_ynab_client):
        """Test parsing empty subtransactions list."""
        result = mock_ynab_client._parse_subtransactions([])
        assert result == []

    def test_parse_single_subtransaction(self, mock_ynab_client):
        """Test parsing a single subtransaction."""
        subtransactions_data = [
            {
                "id": "sub-123",
                "amount": 10000,
                "memo": "Groceries",
                "payee_id": "payee-456",
                "payee_name": "Whole Foods",
                "category_id": "cat-789",
                "category_name": "Groceries",
                "deleted": False,
            }
        ]

        result = mock_ynab_client._parse_subtransactions(subtransactions_data)

        assert len(result) == 1
        assert isinstance(result[0], YNABSubtransaction)
        assert result[0].subtransaction_id == "sub-123"
        assert result[0].amount == Decimal("10000")
        assert result[0].memo == "Groceries"
        assert result[0].payee_id == "payee-456"
        assert result[0].payee_name == "Whole Foods"
        assert result[0].category_id == "cat-789"
        assert result[0].category_name == "Groceries"
        assert result[0].deleted is False

    def test_parse_multiple_subtransactions(self, mock_ynab_client):
        """Test parsing multiple subtransactions."""
        subtransactions_data = [
            {
                "id": "sub-123",
                "amount": 10000,
                "memo": "Groceries",
                "category_id": "cat-groceries",
                "deleted": False,
            },
            {
                "id": "sub-456",
                "amount": 15000,
                "memo": "Gas",
                "category_id": "cat-gas",
                "deleted": False,
            },
        ]

        result = mock_ynab_client._parse_subtransactions(subtransactions_data)

        assert len(result) == 2
        assert result[0].subtransaction_id == "sub-123"
        assert result[0].amount == Decimal("10000")
        assert result[1].subtransaction_id == "sub-456"
        assert result[1].amount == Decimal("15000")

    def test_parse_subtransaction_with_minimal_fields(self, mock_ynab_client):
        """Test parsing subtransaction with only required fields."""
        subtransactions_data = [
            {
                "id": "sub-123",
                "amount": 10000,
            }
        ]

        result = mock_ynab_client._parse_subtransactions(subtransactions_data)

        assert len(result) == 1
        assert result[0].subtransaction_id == "sub-123"
        assert result[0].amount == Decimal("10000")
        assert result[0].memo is None
        assert result[0].category_id is None

    def test_parse_subtransaction_with_transfer(self, mock_ynab_client):
        """Test parsing transfer subtransaction."""
        subtransactions_data = [
            {
                "id": "sub-123",
                "amount": 50000,
                "transfer_account_id": "account-789",
                "transfer_transaction_id": "trans-456",
                "deleted": False,
            }
        ]

        result = mock_ynab_client._parse_subtransactions(subtransactions_data)

        assert len(result) == 1
        assert result[0].amount == Decimal("50000")
        assert result[0].transfer_account_id == "account-789"
        assert result[0].transfer_transaction_id == "trans-456"

    def test_parse_subtransaction_with_invalid_data_skips(self, mock_ynab_client):
        """Test that invalid subtransactions are skipped with warning."""
        subtransactions_data = [
            {
                "id": "sub-123",
                "amount": 10000,
                "memo": "Valid",
            },
            {
                "id": "sub-456",
                # Missing required 'amount' field
                "memo": "Invalid",
            },
            {
                "id": "sub-789",
                "amount": 15000,
                "memo": "Also valid",
            },
        ]

        result = mock_ynab_client._parse_subtransactions(subtransactions_data)

        # Should skip the invalid one
        assert len(result) == 2
        assert result[0].subtransaction_id == "sub-123"
        assert result[1].subtransaction_id == "sub-789"


class TestUpdateTransactionWithSubtransactions:
    """Test update_transaction_with_subtransactions method."""

    def test_update_transaction_with_valid_subtransactions(self, mock_ynab_client):
        """Test updating transaction with valid subtransactions."""
        subtransactions = [
            YNABSubtransaction(
                amount=Decimal("10000"),
                memo="Groceries",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                amount=Decimal("15000"),
                memo="Gas",
                category_id="cat-gas",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        # Mock the API response
        mock_ynab_client._make_request.return_value = {
            "data": {
                "transaction": {
                    "id": "trans-123",
                    "account_id": "account-456",
                    "amount": 25000,
                    "date": "2023-12-01",
                    "cleared": "cleared",
                    "approved": True,
                    "category_id": None,  # Should be null when has subtransactions
                    "subtransactions": [
                        {
                            "id": "sub-new-1",
                            "amount": 10000,
                            "memo": "Groceries",
                            "category_id": "cat-groceries",
                            "deleted": False,
                        },
                        {
                            "id": "sub-new-2",
                            "amount": 15000,
                            "memo": "Gas",
                            "category_id": "cat-gas",
                            "deleted": False,
                        },
                    ],
                }
            }
        }

        result = mock_ynab_client.update_transaction_with_subtransactions(transaction)

        # Verify the request was made correctly
        mock_ynab_client._make_request.assert_called_once()
        call_args = mock_ynab_client._make_request.call_args

        assert call_args[0][0] == "PUT"
        assert "trans-123" in call_args[0][1]

        # Verify request data
        request_data = call_args[1]["json"]["transaction"]
        # category_id should not be in request when has subtransactions (None values removed)
        assert "category_id" not in request_data or request_data["category_id"] is None
        assert len(request_data["subtransactions"]) == 2
        assert request_data["subtransactions"][0]["amount"] == 10000
        assert request_data["subtransactions"][1]["amount"] == 15000

        # Verify result
        assert isinstance(result, YNABTransaction)
        assert result.ynab_id == "trans-123"
        assert len(result.subtransactions) == 2

    def test_update_transaction_with_invalid_subtransaction_sum(self, mock_ynab_client):
        """Test that invalid subtransaction sum raises error."""
        subtransactions = [
            YNABSubtransaction(
                amount=Decimal("10000"),
                memo="Groceries",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                amount=Decimal("12000"),  # Sum is 22000, not 25000
                memo="Gas",
                category_id="cat-gas",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        with pytest.raises(YNABValidationError) as exc_info:
            mock_ynab_client.update_transaction_with_subtransactions(transaction)

        assert "must sum to transaction amount" in str(exc_info.value)

    def test_update_transaction_without_subtransactions(self, mock_ynab_client):
        """Test updating transaction without subtransactions."""
        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            category_id="cat-groceries",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
        )

        # Mock the API response
        mock_ynab_client._make_request.return_value = {
            "data": {
                "transaction": {
                    "id": "trans-123",
                    "account_id": "account-456",
                    "amount": 25000,
                    "date": "2023-12-01",
                    "cleared": "cleared",
                    "approved": True,
                    "category_id": "cat-groceries",
                    "subtransactions": [],
                }
            }
        }

        result = mock_ynab_client.update_transaction_with_subtransactions(transaction)

        # Verify request data
        call_args = mock_ynab_client._make_request.call_args
        request_data = call_args[1]["json"]["transaction"]
        assert request_data["category_id"] == "cat-groceries"
        assert "subtransactions" not in request_data

        # Verify result
        assert result.category_id == "cat-groceries"
        assert len(result.subtransactions) == 0

    def test_update_transaction_with_existing_subtransaction_ids(
        self, mock_ynab_client
    ):
        """Test updating transaction with existing subtransaction IDs."""
        subtransactions = [
            YNABSubtransaction(
                subtransaction_id="sub-existing-1",
                amount=Decimal("10000"),
                memo="Updated groceries",
                category_id="cat-groceries",
            ),
            YNABSubtransaction(
                subtransaction_id="sub-existing-2",
                amount=Decimal("15000"),
                memo="Updated gas",
                category_id="cat-gas",
            ),
        ]

        transaction = YNABTransaction(
            ynab_id="trans-123",
            account_id="account-456",
            amount=Decimal("25000"),
            date=date(2023, 12, 1),
            subtransactions=subtransactions,
        )

        # Mock the API response
        mock_ynab_client._make_request.return_value = {
            "data": {
                "transaction": {
                    "id": "trans-123",
                    "account_id": "account-456",
                    "amount": 25000,
                    "date": "2023-12-01",
                    "cleared": "cleared",
                    "approved": True,
                    "category_id": None,
                    "subtransactions": [
                        {
                            "id": "sub-existing-1",
                            "amount": 10000,
                            "memo": "Updated groceries",
                            "category_id": "cat-groceries",
                            "deleted": False,
                        },
                        {
                            "id": "sub-existing-2",
                            "amount": 15000,
                            "memo": "Updated gas",
                            "category_id": "cat-gas",
                            "deleted": False,
                        },
                    ],
                }
            }
        }

        result = mock_ynab_client.update_transaction_with_subtransactions(transaction)

        # Verify subtransaction IDs were included in request (as 'id', not 'subtransaction_id')
        call_args = mock_ynab_client._make_request.call_args
        request_data = call_args[1]["json"]["transaction"]
        assert request_data["subtransactions"][0]["id"] == "sub-existing-1"
        assert request_data["subtransactions"][1]["id"] == "sub-existing-2"
