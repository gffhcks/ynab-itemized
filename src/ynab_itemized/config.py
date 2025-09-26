"""Configuration management for YNAB Itemized."""

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # YNAB API Configuration
    ynab_api_token: str = Field(default="", description="YNAB API Token")
    ynab_budget_id: str = Field(default="", description="YNAB Budget ID")
    ynab_api_base_url: str = Field(
        default="https://api.youneedabudget.com/v1", description="YNAB API Base URL"
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./ynab_itemized.db", description="Database URL"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log Level")
    log_format: str = Field(default="json", description="Log Format")

    # Application Settings
    debug: bool = Field(default=False, description="Debug Mode")
    backup_enabled: bool = Field(default=True, description="Enable Backups")
    backup_interval_hours: int = Field(
        default=24, description="Backup Interval in Hours"
    )

    # Data Directory
    data_dir: Path = Field(
        default=Path.home() / ".ynab_itemized", description="Data Directory"
    )


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def ensure_data_directory(settings: Optional[Settings] = None) -> Path:
    """Ensure data directory exists and return path."""
    if settings is None:
        settings = get_settings()

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir
