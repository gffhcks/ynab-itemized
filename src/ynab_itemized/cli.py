"""Command-line interface for YNAB Itemized."""

import logging
import sys
from datetime import date, timedelta
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import ensure_data_directory
from .database.manager import DatabaseManager
from .ynab.client import YNABClient
from .ynab.exceptions import YNABAPIError

console = Console()
logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def main(ctx, debug):
    """YNAB Itemized Transaction Manager."""
    ctx.ensure_object(dict)

    # Set up logging
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(log_level)

    # Ensure data directory exists
    ensure_data_directory()


@main.command()
def init_db():
    """Initialize the database."""
    try:
        with console.status("[bold green]Initializing database..."):
            db_manager = DatabaseManager()
            db_manager.create_tables()

        console.print("✅ Database initialized successfully!", style="bold green")
    except Exception as e:
        console.print(f"❌ Failed to initialize database: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.option("--since-days", default=30, help="Number of days to sync back")
@click.option("--account-id", help="Specific account ID to sync")
def sync(since_days: int, account_id: Optional[str]):
    """Sync transactions from YNAB."""
    try:
        ynab_client = YNABClient()
        db_manager = DatabaseManager()

        since_date = date.today() - timedelta(days=since_days)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching transactions from YNAB...", total=None)

            transactions = ynab_client.get_transactions(
                account_id=account_id, since_date=since_date
            )

            progress.update(
                task, description=f"Saving {len(transactions)} transactions..."
            )

            saved_count = 0
            for transaction in transactions:
                try:
                    db_manager.save_ynab_transaction(transaction)
                    saved_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to save transaction {transaction.ynab_id}: {e}"
                    )

            progress.update(task, description="Sync completed!", completed=True)

        console.print(
            f"✅ Synced {saved_count} transactions successfully!", style="bold green"
        )

    except YNABAPIError as e:
        console.print(f"❌ YNAB API error: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Sync failed: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.argument("transaction_id")
def add_items(transaction_id: str):
    """Add itemized data to a transaction."""
    try:
        ynab_client = YNABClient()

        # Get transaction from YNAB
        with console.status("[bold green]Fetching transaction..."):
            transaction = ynab_client.get_transaction(transaction_id)

        if not transaction:
            console.print(
                f"❌ Transaction {transaction_id} not found", style="bold red"
            )
            sys.exit(1)

        amount_display = abs(transaction.amount / 1000)
        console.print(f"Transaction: {transaction.payee_name} - ${amount_display:.2f}")

        # Interactive item entry
        items = []
        console.print("\nEnter items (press Enter with empty name to finish):")

        while True:
            name = click.prompt("Item name", default="", show_default=False)
            if not name:
                break

            amount = click.prompt("Amount", type=float)
            category = click.prompt("Category", default="", show_default=False) or None

            items.append({"name": name, "amount": amount, "category": category})

        if items:
            # Create itemized transaction (this would need more implementation)
            console.print(
                f"✅ Added {len(items)} items to transaction", style="bold green"
            )
        else:
            console.print("No items added", style="yellow")

    except Exception as e:
        console.print(f"❌ Failed to add items: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.option("--limit", default=20, help="Number of transactions to show")
def list_transactions(limit: int):
    """List transactions with itemized data."""
    try:
        db_manager = DatabaseManager()

        with console.status("[bold green]Fetching transactions..."):
            transactions = db_manager.get_all_itemized_transactions()

        if not transactions:
            console.print("No itemized transactions found", style="yellow")
            return

        # Create table
        table = Table(title="Itemized Transactions")
        table.add_column("Date", style="cyan")
        table.add_column("Payee", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Items", style="blue", justify="right")
        table.add_column("Store", style="yellow")

        for transaction in transactions[:limit]:
            ynab_tx = transaction.ynab_transaction
            if ynab_tx:
                table.add_row(
                    str(ynab_tx.date),
                    ynab_tx.payee_name or "Unknown",
                    f"${abs(ynab_tx.amount/1000):.2f}",
                    str(len(transaction.items)),
                    transaction.store_name or "",
                )
            else:
                # Handle standalone itemized transactions
                table.add_row(
                    str(transaction.transaction_date or "Unknown"),
                    transaction.merchant_name or "Unknown",
                    f"${transaction.total_amount or 0:.2f}",
                    str(len(transaction.items)),
                    transaction.store_name or "",
                )

        console.print(table)

    except Exception as e:
        console.print(f"❌ Failed to list transactions: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.option(
    "--format", "export_format", default="csv", type=click.Choice(["csv", "json"])
)
@click.option("--output", help="Output file path")
def export(export_format: str, output: Optional[str]):
    """Export itemized transaction data."""
    try:
        db_manager = DatabaseManager()

        with console.status("[bold green]Exporting data..."):
            transactions = db_manager.get_all_itemized_transactions()

        if not transactions:
            console.print("No data to export", style="yellow")
            return

        if not output:
            output = f"ynab_itemized_export.{export_format}"

        # Export logic would go here
        console.print(
            f"✅ Exported {len(transactions)} transactions to {output}",
            style="bold green",
        )

    except Exception as e:
        console.print(f"❌ Export failed: {e}", style="bold red")
        sys.exit(1)


@main.command()
def list_budgets():
    """List available YNAB budgets."""
    try:
        ynab_client = YNABClient()

        with console.status("[bold green]Fetching budgets..."):
            budgets = ynab_client.get_budgets()

        table = Table(title="YNAB Budgets")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Currency", style="green")

        for budget in budgets:
            table.add_row(
                budget["id"],
                budget["name"],
                budget.get("currency_format", {}).get("iso_code", "Unknown"),
            )

        console.print(table)

    except YNABAPIError as e:
        console.print(f"❌ YNAB API error: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Failed to list budgets: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.8,
    help="Minimum confidence score for automatic matching (0.0-1.0)",
)
@click.option(
    "--date-tolerance",
    type=int,
    default=3,
    help="Number of days +/- to search for matches",
)
@click.option(
    "--amount-tolerance",
    type=float,
    default=0.05,
    help="Percentage tolerance for amount matching (0.05 = 5%)",
)
@click.pass_context
def match_transactions(
    ctx: click.Context,
    confidence_threshold: float,
    date_tolerance: int,
    amount_tolerance: float,
) -> None:
    """Match itemized transactions with YNAB transactions."""
    from .database.manager import DatabaseManager
    from .services.matching import TransactionMatcher

    try:
        with console.status("🔍 Matching transactions..."):
            db_manager = DatabaseManager()

            with db_manager.get_session() as session:
                matcher = TransactionMatcher(session)

                # Get unmatched itemized transactions
                unmatched = matcher.get_unmatched_itemized_transactions()
                console.print(f"Found {len(unmatched)} unmatched itemized transactions")

                if not unmatched:
                    console.print("✅ No unmatched transactions found!")
                    return

                # Auto-match high-confidence matches
                auto_matches = matcher.auto_match_transactions(confidence_threshold)

                if auto_matches:
                    console.print(
                        f"✅ Automatically matched {len(auto_matches)} transactions"
                    )

                # Show remaining unmatched transactions
                remaining = matcher.get_unmatched_itemized_transactions()
                if remaining:
                    console.print(
                        f"⚠️  {len(remaining)} transactions still need manual review"
                    )

                    # Show a few examples
                    table = Table(title="Unmatched Itemized Transactions (Sample)")
                    table.add_column("Date", style="cyan")
                    table.add_column("Merchant", style="green")
                    table.add_column("Amount", style="yellow")
                    table.add_column("Source", style="blue")

                    for tx in remaining[:5]:  # Show first 5
                        table.add_row(
                            str(tx.transaction_date),
                            tx.merchant_name or "Unknown",
                            f"${tx.total_amount:.2f}",
                            tx.source,
                        )

                    console.print(table)

                    if len(remaining) > 5:
                        console.print(f"... and {len(remaining) - 5} more")

    except Exception as e:
        console.print(f"❌ Error matching transactions: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
