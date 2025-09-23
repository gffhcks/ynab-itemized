# YNAB Itemized Transaction Manager

A Python application for managing itemized transaction data with YNAB (You Need A Budget) integration.

## Features

- **YNAB Integration**: Read and write transaction data to/from YNAB
- **Itemized Storage**: Store detailed transaction breakdowns including:
  - Item subtotals
  - Tax amounts
  - Discounts and promotions
  - Additional metadata (store info, categories, etc.)
- **Local Database**: SQLite-based storage for offline access and detailed records
- **Data Validation**: Pydantic models for robust data handling
- **CLI Interface**: Command-line tools for easy interaction

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ynab-itemized
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Set up configuration:
```bash
cp .env.example .env
# Edit .env with your YNAB API token and budget ID
```

5. Initialize the database:
```bash
ynab-itemized init-db
```

## Configuration

### YNAB API Setup

1. Go to [YNAB Developer Settings](https://app.youneedabudget.com/settings/developer)
2. Generate a Personal Access Token
3. Find your Budget ID in the YNAB URL or use the CLI to list budgets
4. Update your `.env` file with these values

## Usage

### Command Line Interface

```bash
# Initialize database
ynab-itemized init-db

# Sync transactions from YNAB
ynab-itemized sync

# Add itemized data to a transaction
ynab-itemized add-items TRANSACTION_ID

# List transactions with itemized data
ynab-itemized list-transactions

# Export data
ynab-itemized export --format csv --output transactions.csv
```

### Python API

```python
from ynab_itemized import YNABClient, ItemizedTransaction

# Initialize client
client = YNABClient(api_token="your_token", budget_id="your_budget_id")

# Fetch transactions
transactions = client.get_transactions()

# Add itemized data
itemized = ItemizedTransaction(
    transaction_id="transaction_id",
    items=[
        {"name": "Item 1", "amount": 10.99, "category": "Groceries"},
        {"name": "Item 2", "amount": 5.50, "category": "Groceries"},
    ],
    tax_amount=1.32,
    discount_amount=0.00
)
```

## Development

### Setup Development Environment

```bash
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

## Project Structure

```
ynab-itemized/
├── src/ynab_itemized/          # Main package
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   ├── config.py               # Configuration management
│   ├── models/                 # Data models
│   ├── database/               # Database operations
│   ├── ynab/                   # YNAB API integration
│   └── utils/                  # Utility functions
├── tests/                      # Test suite
├── alembic/                    # Database migrations
├── docs/                       # Documentation
├── requirements.txt            # Dependencies
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## License

MIT License - see LICENSE file for details.
