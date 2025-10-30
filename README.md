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

### Quick Setup (Cross-Platform)

This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable Python package and project management. We provide automated setup scripts for all major platforms:

#### Windows (PowerShell)
```powershell
git clone <repository-url>
cd ynab-itemized
.\scripts\setup-windows.ps1 -DevSetup
```

#### Linux/macOS (Bash)
```bash
git clone <repository-url>
cd ynab-itemized
./scripts/setup-unix.sh --dev-setup
```

The setup scripts will automatically install UV and Nox, then set up your development environment.

#### Manual Setup with UV
If you already have UV installed:

```bash
git clone <repository-url>
cd ynab-itemized
uv tool install nox
nox -s dev_setup
```

### Manual Installation

1. **Prerequisites**
   - Python 3.9 or higher
   - Git
   - pip

2. **Clone the repository:**
```bash
git clone <repository-url>
cd ynab-itemized
```

3. **Install system dependencies:**

   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install -y python3-dev python3-venv python3-pip build-essential git
   ```

   **RHEL/CentOS/Fedora:**
   ```bash
   sudo dnf install -y python3-devel python3-pip gcc gcc-c++ make git
   ```

   **macOS (with Homebrew):**
   ```bash
   brew install python git
   ```

   **Windows:**
   - Install Python from [python.org](https://python.org)
   - Install Git from [git-scm.com](https://git-scm.com)

4. **Install the Python package:**
```bash
make install
```

### Alternative: Direct Installation with UV

If you prefer to manage the environment directly with UV:

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh  # Unix/macOS
# or
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Create a virtual environment and install the package
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"  # For development
# or
uv pip install .  # For regular use
```

## Configuration

After installation, set up your configuration:
```bash
cp .env.example .env
# Edit .env with your YNAB API token and budget ID
```

Initialize the database:
```bash
ynab-itemized init-db
```

## Development

### Package Management with UV

This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable package management. UV provides:
- **10-100x faster** package installation than pip
- **Reliable dependency resolution** with a built-in resolver
- **Drop-in replacement** for pip, pip-tools, and virtualenv
- **Cross-platform** support for Windows, macOS, and Linux

### Code Quality with Pre-commit

This project uses [pre-commit](https://pre-commit.com/) to automatically run linters and formatters before each commit:
- **black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting and style checking
- **mypy** - Static type checking
- **Standard hooks** - Trailing whitespace, end-of-file fixes, YAML validation, etc.

Pre-commit is automatically installed and configured by the setup scripts. To run manually:
```bash
pre-commit run --all-files  # Run all hooks on all files
pre-commit run              # Run hooks on staged files only
```

### Available Nox Sessions

The project uses [Nox](https://nox.thea.codes/) with UV backend for cross-platform development tasks:

```bash
nox --list         # Show all available sessions
nox -s dev_setup   # Set up development environment
nox -s tests       # Run tests
nox -s lint        # Run linting (flake8) - for CI/testing
nox -s type_check  # Run type checking (mypy) - for CI/testing
nox -s format      # Format code with black and isort - for CI/testing
nox -s format_check # Check code formatting - for CI/testing
nox -s build       # Build package
nox -s clean       # Clean build artifacts
nox -s pre_commit  # Run all pre-commit checks + tests
```

**Note**: For local development, use `pre-commit run --all-files` instead of individual nox linting sessions. The nox linting sessions are kept for CI/CD pipelines and testing purposes.

### Cross-Platform Development

Nox with UV backend automatically handles:
- Fast virtual environment creation with UV
- Cross-platform path handling
- Python version management
- Rapid dependency installation

This ensures consistent behavior across Windows, macOS, and Linux with significantly improved performance.

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

### Quick Development Setup

For a complete development environment setup:

```bash
# Using nox with UV (recommended)
nox -s dev_setup

# Or manually with UV
uv pip install -e ".[dev]"
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
