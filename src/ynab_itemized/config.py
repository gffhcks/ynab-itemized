"""Configuration management for YNAB Itemized."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # YNAB API Configuration
    ynab_api_token: str = Field(..., env="YNAB_API_TOKEN")
    ynab_budget_id: str = Field(..., env="YNAB_BUDGET_ID")
    ynab_api_base_url: str = Field(
        default="https://api.youneedabudget.com/v1",
        env="YNAB_API_BASE_URL"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./ynab_itemized.db",
        env="DATABASE_URL"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Application Settings
    debug: bool = Field(default=False, env="DEBUG")
    backup_enabled: bool = Field(default=True, env="BACKUP_ENABLED")
    backup_interval_hours: int = Field(default=24, env="BACKUP_INTERVAL_HOURS")
    
    # Data Directory
    data_dir: Path = Field(default=Path.home() / ".ynab_itemized")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def ensure_data_directory(settings: Optional[Settings] = None) -> Path:
    """Ensure data directory exists and return path."""
    if settings is None:
        settings = get_settings()
    
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir
