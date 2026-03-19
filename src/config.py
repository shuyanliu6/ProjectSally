"""
Configuration management for Project Sally.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from datetime import datetime


class Config(BaseSettings):
    """Application configuration from environment variables."""

    # Database Configuration
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_user: str = Field(default="stock_user", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_name: str = Field(default="stock_picking_system", alias="DB_NAME")

    # Data Provider Configuration
    data_provider: str = Field(default="yfinance", alias="DATA_PROVIDER")
    eodhd_api_key: Optional[str] = Field(default=None, alias="EODHD_API_KEY")
    polygon_api_key: Optional[str] = Field(default=None, alias="POLYGON_API_KEY")
    alpha_vantage_api_key: Optional[str] = Field(default=None, alias="ALPHA_VANTAGE_API_KEY")
    massive_api_key: Optional[str] = Field(default=None, alias="MASSIVE_API_KEY")
    massive_base_url: str = Field(default="https://api.massive.com", alias="MASSIVE_BASE_URL")

    # Application Configuration
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=True, alias="DEBUG")

    # Data Configuration
    start_date: str = Field(default="2015-01-01", alias="START_DATE")
    end_date: str = Field(default="2024-12-31", alias="END_DATE")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Generate database connection URL."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"


def get_config() -> Config:
    """Get application configuration."""
    return Config()
