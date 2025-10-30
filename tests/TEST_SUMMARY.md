# Test Summary

## Overview

This document summarizes the comprehensive test suite for the YNAB Itemized project.

**Total Tests: 99** (94 unit + 5 integration)

## Phase 1: YNAB Subtransaction Integration (Complete ✅)

Phase 1 (Tasks 1.1-1.9) implements subtransaction support and basic CLI commands.

## Test Files Created

### 1. `tests/unit/test_subtransactions.py` (14 tests)

Tests for the Pydantic models (`YNABSubtransaction` and `YNABTransaction`).

**Test Classes:**
- `TestYNABSubtransaction` (4 tests)
  - Basic subtransaction creation
  - Subtransaction with all fields
  - Amount conversion (int, float, string → Decimal)
  - Transfer subtransactions

- `TestYNABTransactionWithSubtransactions` (7 tests)
  - Transactions without subtransactions
  - Valid subtransactions (amounts sum correctly)
  - Invalid subtransaction sums
  - Multiple subtransactions (3-way splits)
  - Negative amounts (refunds)
  - Empty subtransactions list
  - Payee overrides in subtransactions

- `TestSubtransactionEdgeCases` (3 tests)
  - Zero amount subtransactions
  - Very large amounts
  - Minimal required fields

### 2. `tests/unit/test_ynab_client_subtransactions.py` (10 tests)

Tests for YNAB client subtransaction functionality.

**Test Classes:**
- `TestParseSubtransactions` (6 tests)
  - Parsing empty subtransactions list
  - Parsing single subtransaction
  - Parsing multiple subtransactions
  - Parsing with minimal fields
  - Parsing transfer subtransactions
  - Handling invalid data (skips with warning)

- `TestUpdateTransactionWithSubtransactions` (4 tests)
  - Updating transaction with valid subtransactions
  - Validation error for invalid subtransaction sum
  - Updating transaction without subtransactions
  - Updating with existing subtransaction IDs

### 3. `tests/unit/test_database_subtransactions.py` (15 tests)

Tests for database schema changes supporting subtransactions.

### 4. `tests/unit/test_subtransaction_service.py` (11 tests)

Tests for SubtransactionService business logic.

**Test Classes:**
- `TestCreateSubtransactionsFromItems` (9 tests)
  - Creating basic subtransactions from items
  - Creating subtransactions with tax
  - Creating subtransactions with discount
  - Creating subtransactions with both tax and discount
  - Validating subtransactions sum to total
  - Automatic rounding adjustment (up to 1 cent)
  - Error on large rounding differences
  - Handling empty items list
  - Single item conversion

- `TestSyncSubtransactionsToYNAB` (2 tests)
  - Successful sync to YNAB
  - Dry run mode (no actual sync)

### 5. `tests/unit/test_cli_subtransactions.py` (8 tests)

Tests for CLI commands for subtransaction management.

**Test Classes:**
- `TestCreateSubtransactionsCommand` (4 tests)
  - Successful creation of subtransactions
  - Dry-run mode (preview only)
  - Transaction not found error
  - Custom options (--no-tax, --no-discount)

- `TestSyncSubtransactionsCommand` (2 tests)
  - Successful sync from YNAB
  - Transaction not found error

- `TestRemoveSubtransactionsCommand` (2 tests)
  - Successful removal of subtransactions
  - No subtransactions to remove

### 6. `tests/unit/test_database_subtransactions.py` (15 tests)

Tests for database schema changes supporting subtransactions.

**Test Classes:**
- `TestYNABTransactionDBSchema` (4 tests)
  - `has_subtransactions` field exists
  - Default value is False
  - Can be set to True
  - Can be updated

- `TestItemizedTransactionDBSchema` (4 tests)
  - `subtransactions_synced_at` field exists
  - Default value is NULL
  - Can be set to datetime
  - Can be updated

- `TestTransactionItemDBSchema` (7 tests)
  - `ynab_subtransaction_id` field exists
  - `ynab_category_id` field exists
  - Index on `ynab_subtransaction_id` exists
  - Creating items without subtransaction mapping
  - Creating items with subtransaction mapping
  - Querying items by subtransaction ID (uses index)
  - Updating subtransaction mapping

## Test Coverage

### Models (`src/ynab_itemized/models/transaction.py`)
✅ `YNABSubtransaction` model
  - Field validation
  - Amount conversion
  - Transfer fields
  - Deleted flag

✅ `YNABTransaction` model
  - `subtransactions` field
  - `has_subtransactions` property
  - `validate_subtransaction_amounts()` method
  - `dict_for_db()` method (excludes subtransactions, sets has_subtransactions flag)

### YNAB Client (`src/ynab_itemized/ynab/client.py`)
✅ `_parse_subtransactions()` method
  - Parsing from API response
  - Handling missing fields
  - Error handling for invalid data

✅ `update_transaction_with_subtransactions()` method
  - Validation of subtransaction amounts
  - Setting category_id to null when has subtransactions
  - Formatting subtransactions for API
  - Handling existing subtransaction IDs
  - Removing None values from request

### Database Schema (`src/ynab_itemized/database/models.py`)
✅ `YNABTransactionDB` model
  - `has_subtransactions` field (BOOLEAN, NOT NULL, default=False)

✅ `ItemizedTransactionDB` model
  - `subtransactions_synced_at` field (DATETIME, NULL)

✅ `TransactionItemDB` model
  - `ynab_subtransaction_id` field (VARCHAR, NULL, indexed)
  - `ynab_category_id` field (VARCHAR, NULL)

### Database Migration
✅ Alembic migration (`alembic/versions/64fa28c8949c_initial_schema.py`)
  - Creates all tables with subtransaction fields
  - Tested upgrade and downgrade

### SubtransactionService (`src/ynab_itemized/services/subtransaction.py`)
✅ `create_subtransactions_from_items()` method
  - Converts TransactionItem objects to YNABSubtransaction objects
  - Handles amount conversion (dollars to milliunits)
  - Makes amounts negative for expenses (YNAB convention)
  - Creates separate tax subtransaction (optional)
  - Creates separate discount subtransaction (optional, positive amount)
  - Validates subtransaction amounts sum to total
  - Automatically adjusts for small rounding errors (≤1 cent)
  - Raises error for large discrepancies (>1 cent)

✅ `sync_subtransactions_to_ynab()` method
  - Updates YNAB transaction with subtransactions
  - Supports dry-run mode
  - Logs operations

## Test Results

**Total Tests:** 76 (including existing tests)
**New Tests:** 63
**Status:** ✅ All tests passing

### Breakdown:

**Unit Tests (71 tests):**
- `test_subtransactions.py`: 14/14 passed
- `test_ynab_client_subtransactions.py`: 10/10 passed
- `test_database_subtransactions.py`: 15/15 passed
- `test_subtransaction_service.py`: 11/11 passed ✨ NEW
- `test_cli_subtransactions.py`: 8/8 passed ✨ NEW
- `test_database.py`: 6/6 passed (existing tests, verified no regression)
- `test_models.py`: 7/7 passed (existing tests, verified no regression)

**Integration Tests (5 tests):** ✨ NEW
- `test_subtransaction_workflow.py`: 5/5 passed

## Key Testing Patterns

### 1. Model Validation Testing
- Test valid inputs
- Test invalid inputs (expect validation errors)
- Test edge cases (zero, negative, very large values)
- Test type conversions (int/float/string → Decimal)

### 2. Database Schema Testing
- Verify field existence using SQLAlchemy inspector
- Verify field types and constraints
- Verify indexes exist
- Test CRUD operations
- Test queries using indexes

### 3. API Client Testing
- Mock API responses
- Verify request formatting
- Test error handling
- Test data parsing

### 4. Integration Testing
- Test data flow from model → database
- Test data flow from API → model
- Verify no regressions in existing functionality

## Test Fixtures

### From `tests/conftest.py`:
- `sample_ynab_transaction`: Sample YNAB transaction for testing
- `sample_itemized_transaction`: Sample itemized transaction with items
- `test_db`: In-memory SQLite database for testing

### New Fixtures in Test Files:
- `mock_ynab_client`: Mocked YNAB client with `_make_request` stubbed
- `db_session`: In-memory database session for schema testing

## Running the Tests

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run specific test file
uv run pytest tests/unit/test_subtransactions.py -v

# Run with coverage
uv run pytest tests/unit/ --cov=src/ynab_itemized --cov-report=html

# Run specific test class
uv run pytest tests/unit/test_subtransactions.py::TestYNABSubtransaction -v

# Run specific test
uv run pytest tests/unit/test_subtransactions.py::TestYNABSubtransaction::test_create_basic_subtransaction -v
```

## Integration Tests

### `tests/integration/test_subtransaction_workflow.py` (5 tests)

End-to-end integration tests for complete subtransaction workflow.

**Test Class:**
- `TestEndToEndSubtransactionWorkflow` (5 tests)
  - Create and sync subtransactions (full workflow)
  - Create subtransactions with tax and discount
  - Round-trip save and retrieve from database
  - Dry-run mode (no actual API calls)
  - Error handling for invalid amounts

## MVP: Amazon Import (Complete ✅)

Amazon Request My Data import functionality for loading itemized transactions.

### 8. `tests/unit/test_store_integration_base.py` (5 tests)

Tests for the abstract `StoreIntegration` base class.

**Test Class:**
- `TestStoreIntegration` (5 tests)
  - Verify abstract class cannot be instantiated
  - Verify concrete implementations must implement all methods
  - Test default `get_supported_date_range()` (90 days)
  - Test overriding `get_supported_date_range()`
  - Test concrete implementation with all methods

### 9. `tests/unit/test_amazon_integration.py` (12 tests)

Tests for Amazon Request My Data CSV integration.

**Test Class:**
- `TestAmazonRequestMyDataIntegration` (12 tests)
  - Store name property ("Amazon")
  - Integration type property ("csv")
  - Supported date range (10+ years)
  - Parse CSV file with multiple orders
  - Parse empty CSV
  - Error handling: missing columns
  - Error handling: invalid date format
  - Error handling: invalid amounts
  - Parse data method (abstract implementation)
  - Group items by order ID
  - Parse single order
  - Parse order with multiple items

### 10. `tests/unit/test_cli_import_amazon.py` (6 tests)

Tests for the `import-amazon` CLI command.

**Test Class:**
- `TestImportAmazonCommand` (6 tests)
  - Successful import with --yes flag
  - Dry-run mode (preview only)
  - Error handling: file not found
  - Error handling: parse errors
  - Handle empty CSV (no transactions)
  - Confirmation prompt (without --yes)

## Phase 1 Completion Status

✅ **Task 1.1**: Add YNABSubtransaction model - COMPLETE
✅ **Task 1.2**: Update YNABTransaction model - COMPLETE
✅ **Task 1.3**: Update YNAB client - COMPLETE
✅ **Task 1.4**: Add update_transaction_with_subtransactions method - COMPLETE
✅ **Task 1.5**: Update database schema - COMPLETE
✅ **Task 1.6**: Create Alembic migration - COMPLETE
✅ **Task 1.7**: Create SubtransactionService - COMPLETE
✅ **Task 1.8**: Add CLI commands - COMPLETE
✅ **Task 1.9**: Write integration tests - COMPLETE

**Phase 1: YNAB Subtransaction Integration is 100% COMPLETE! 🎉**

## MVP Completion Status

✅ **Amazon Integration**: Store integration base class - COMPLETE
✅ **Amazon Integration**: Amazon Request My Data parser - COMPLETE
✅ **Amazon Integration**: CLI import command - COMPLETE

**MVP: Amazon Import is 100% COMPLETE! 🎉**

## Notes

- All tests use in-memory SQLite databases for speed and isolation
- Tests are independent and can run in any order
- Mock objects are used to avoid external API calls
- Tests verify both happy paths and error conditions
- Database schema tests use SQLAlchemy inspector for verification
- All existing tests continue to pass (no regressions)
- Amazon CSV parser handles grouping items by Order ID
- CLI provides preview, dry-run, and confirmation prompts
