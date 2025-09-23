"""Formatting utilities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional


def format_currency(amount: Decimal, currency_symbol: str = "$") -> str:
    """Format currency amount for display."""
    if amount is None:
        return "N/A"
    
    # Handle negative amounts
    if amount < 0:
        return f"-{currency_symbol}{abs(amount):.2f}"
    else:
        return f"{currency_symbol}{amount:.2f}"


def format_date(date_obj: Optional[date], format_str: str = "%Y-%m-%d") -> str:
    """Format date for display."""
    if date_obj is None:
        return "N/A"
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    return date_obj.strftime(format_str)


def format_percentage(value: Optional[Decimal], decimal_places: int = 2) -> str:
    """Format percentage for display."""
    if value is None:
        return "N/A"
    
    return f"{value:.{decimal_places}f}%"


def truncate_string(text: Optional[str], max_length: int = 50) -> str:
    """Truncate string for display."""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."
