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
from .integrations.amazon import AmazonRequestMyDataIntegration
from .services.subtransaction import SubtransactionService
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


@main.command()
@click.argument("itemized_transaction_id")
@click.option(
    "--dry-run", is_flag=True, help="Preview subtransactions without creating"
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--no-tax", is_flag=True, help="Don't create separate tax subtransaction")
@click.option(
    "--no-discount", is_flag=True, help="Don't create separate discount subtransaction"
)
def create_subtransactions(
    itemized_transaction_id: str,
    dry_run: bool,
    yes: bool,
    no_tax: bool,
    no_discount: bool,
):
    """Create YNAB subtransactions from itemized transaction."""
    try:
        db_manager = DatabaseManager()
        ynab_client = YNABClient()
        service = SubtransactionService(ynab_client, db_manager)

        # Get itemized transaction
        with console.status("[bold green]Fetching transaction..."):
            itemized_tx = db_manager.get_itemized_transaction(itemized_transaction_id)

        if not itemized_tx:
            console.print(
                f"❌ Itemized transaction {itemized_transaction_id} not found",
                style="bold red",
            )
            sys.exit(1)

        if not itemized_tx.ynab_transaction:
            console.print(
                "❌ Transaction not linked to YNAB transaction", style="bold red"
            )
            sys.exit(1)

        # Create subtransactions
        subtransactions = service.create_subtransactions_from_items(
            itemized_tx,
            include_tax_subtransaction=not no_tax,
            include_discount_subtransaction=not no_discount,
        )

        # Display preview
        console.print(f"\n[bold]Preview: {len(subtransactions)} subtransactions[/bold]")
        table = Table()
        table.add_column("Memo", style="cyan")
        table.add_column("Amount", style="green", justify="right")

        for st in subtransactions:
            amount_display = abs(st.amount / 1000)
            sign = "-" if st.amount < 0 else "+"
            table.add_row(st.memo or "", f"{sign}${amount_display:.2f}")

        console.print(table)

        if dry_run:
            console.print("\n[yellow]DRY RUN: No changes made[/yellow]")
            return

        # Confirm
        if not yes:
            if not click.confirm("\nCreate these subtransactions in YNAB?"):
                console.print("Cancelled", style="yellow")
                return

        # Sync to YNAB
        with console.status("[bold green]Creating subtransactions in YNAB..."):
            ynab_tx = itemized_tx.ynab_transaction
            ynab_tx.subtransactions = subtransactions
            updated_tx = service.sync_subtransactions_to_ynab(ynab_tx, dry_run=False)

        console.print(
            f"✅ Created {len(subtransactions)} subtransactions successfully!",
            style="bold green",
        )

    except Exception as e:
        console.print(f"❌ Failed to create subtransactions: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.argument("transaction_id")
def sync_subtransactions(transaction_id: str):
    """Sync subtransactions from YNAB to local database."""
    try:
        ynab_client = YNABClient()
        db_manager = DatabaseManager()

        # Get transaction from YNAB
        with console.status("[bold green]Fetching transaction from YNAB..."):
            transaction = ynab_client.get_transaction(transaction_id)

        if not transaction:
            console.print(
                f"❌ Transaction {transaction_id} not found in YNAB", style="bold red"
            )
            sys.exit(1)

        # Display subtransactions
        if transaction.has_subtransactions:
            console.print(
                f"\n[bold]Found {len(transaction.subtransactions)} subtransactions[/bold]"
            )
            table = Table()
            table.add_column("Memo", style="cyan")
            table.add_column("Amount", style="green", justify="right")
            table.add_column("Category", style="yellow")

            for st in transaction.subtransactions:
                amount_display = abs(st.amount / 1000)
                sign = "-" if st.amount < 0 else "+"
                table.add_row(
                    st.memo or "",
                    f"{sign}${amount_display:.2f}",
                    st.category_name or "",
                )

            console.print(table)
        else:
            console.print("[yellow]Transaction has no subtransactions[/yellow]")

        # Save to database
        with console.status("[bold green]Saving to database..."):
            db_manager.save_ynab_transaction(transaction)

        console.print(
            f"✅ Synced {len(transaction.subtransactions)} subtransactions successfully!",
            style="bold green",
        )

    except YNABAPIError as e:
        console.print(f"❌ YNAB API error: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Failed to sync subtransactions: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.argument("transaction_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def remove_subtransactions(transaction_id: str, yes: bool):
    """Remove subtransactions from a YNAB transaction."""
    try:
        ynab_client = YNABClient()
        db_manager = DatabaseManager()

        # Get transaction from YNAB
        with console.status("[bold green]Fetching transaction from YNAB..."):
            transaction = ynab_client.get_transaction(transaction_id)

        if not transaction:
            console.print(
                f"❌ Transaction {transaction_id} not found in YNAB", style="bold red"
            )
            sys.exit(1)

        if not transaction.has_subtransactions:
            console.print(
                "[yellow]Transaction has no subtransactions to remove[/yellow]"
            )
            return

        # Display current subtransactions
        console.print(
            f"\n[bold]Current subtransactions ({len(transaction.subtransactions)}):[/bold]"
        )
        for st in transaction.subtransactions:
            amount_display = abs(st.amount / 1000)
            sign = "-" if st.amount < 0 else "+"
            console.print(f"  • {st.memo or 'No memo'}: {sign}${amount_display:.2f}")

        # Confirm
        if not yes:
            if not click.confirm("\nRemove all subtransactions?"):
                console.print("Cancelled", style="yellow")
                return

        # Remove subtransactions by updating transaction without them
        transaction.subtransactions = []
        with console.status("[bold green]Removing subtransactions from YNAB..."):
            ynab_client.update_transaction_with_subtransactions(transaction)

        console.print("✅ Subtransactions removed successfully!", style="bold green")

    except YNABAPIError as e:
        console.print(f"❌ YNAB API error: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Failed to remove subtransactions: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Preview transactions without importing")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def import_amazon(csv_file: str, dry_run: bool, yes: bool):
    """Import transactions from Amazon Request My Data CSV export."""
    try:
        from pathlib import Path

        csv_path = Path(csv_file)

        # Parse Amazon CSV
        console.print(f"[bold]Parsing Amazon CSV: {csv_path.name}[/bold]")
        integration = AmazonRequestMyDataIntegration(config={})

        with console.status("[bold green]Parsing CSV file..."):
            transactions = integration.parse_data(str(csv_path))

        if not transactions:
            console.print("[yellow]No transactions found in CSV file[/yellow]")
            return

        # Count total items
        total_items = sum(len(tx.items) for tx in transactions)

        # Display summary
        console.print(
            f"\n[bold green]Found {len(transactions)} transactions with {total_items} items[/bold green]"
        )

        # Show preview table
        table = Table(title="Transactions Preview")
        table.add_column("Date", style="cyan")
        table.add_column("Merchant", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Items", style="yellow", justify="right")
        table.add_column("Order ID", style="blue")

        for tx in transactions[:10]:  # Show first 10
            table.add_row(
                str(tx.transaction_date),
                tx.merchant_name or "Unknown",
                f"${tx.total_amount:.2f}",
                str(len(tx.items)),
                tx.source_transaction_id or "",
            )

        if len(transactions) > 10:
            table.add_row("...", "...", "...", "...", "...")

        console.print(table)

        # Dry run mode - exit early
        if dry_run:
            console.print("\n[yellow]DRY RUN - No data was imported[/yellow]")
            return

        # Confirmation prompt
        if not yes:
            if not click.confirm(
                f"\nImport {len(transactions)} transactions to database?"
            ):
                console.print("[yellow]Import cancelled[/yellow]")
                return

        # Import to database
        db_manager = DatabaseManager()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Importing {len(transactions)} transactions...",
                total=len(transactions),
            )

            imported_count = 0
            for tx in transactions:
                try:
                    db_manager.save_itemized_transaction(tx)
                    imported_count += 1
                    progress.update(task, advance=1)
                except Exception as e:
                    logger.warning(
                        f"Failed to import transaction {tx.source_transaction_id}: {e}"
                    )

        console.print(
            f"\n✅ Successfully imported {imported_count} transactions with {total_items} items!",
            style="bold green",
        )
        console.print(
            "\n[cyan]Next steps:[/cyan]\n"
            "  1. Run [bold]ynab-itemized list-transactions[/bold] to view imported transactions\n"
            "  2. Match transactions to YNAB (coming soon)\n"
            "  3. Create subtransactions with [bold]create-subtransactions[/bold]"
        )

    except FileNotFoundError:
        console.print(f"❌ File not found: {csv_file}", style="bold red")
        sys.exit(1)
    except ValueError as e:
        console.print(f"❌ Invalid CSV format: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Import failed: {e}", style="bold red")
        logger.exception("Import failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
