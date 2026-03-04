"""Data provider connectors for various sources."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import yfinance as yf
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataProvider(ABC):
    """Abstract base class for data providers."""

    @abstractmethod
    def get_daily_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV data."""
        pass

    @abstractmethod
    def get_dividends(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch dividend history."""
        pass

    @abstractmethod
    def get_splits(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch stock split history."""
        pass

    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker exists."""
        pass


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance data provider using yfinance library."""

    def __init__(self):
        self.name = "yfinance"
        self.base_url = "https://finance.yahoo.com"

    def get_daily_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV data from Yahoo Finance."""
        try:
            logger.info(f"Fetching daily prices for {ticker} from {start_date} to {end_date}")
            
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False,  # Keep unadjusted prices
            )
            
            if data.empty:
                logger.warning(f"No data found for ticker {ticker}")
                return pd.DataFrame()
            
            # Rename columns to match our schema
            data = data.rename(columns={
                "Open": "open_price",
                "High": "high_price",
                "Low": "low_price",
                "Close": "close_price",
                "Adj Close": "adj_close_price",
                "Volume": "volume",
            })
            
            # Reset index to make date a column
            data = data.reset_index()
            data = data.rename(columns={"Date": "date"})
            
            # Convert date to date object
            data["date"] = pd.to_datetime(data["date"]).dt.date
            
            # Add metadata
            data["data_source"] = self.name
            data["is_adjusted"] = False
            
            logger.info(f"Successfully fetched {len(data)} records for {ticker}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching daily prices for {ticker}: {e}")
            return pd.DataFrame()

    def get_dividends(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch dividend history from Yahoo Finance."""
        try:
            logger.info(f"Fetching dividends for {ticker}")
            
            stock = yf.Ticker(ticker)
            dividends = stock.dividends
            
            if dividends.empty:
                logger.info(f"No dividends found for {ticker}")
                return pd.DataFrame()
            
            # Filter by date range
            dividends = dividends[
                (dividends.index.date >= start_date) & 
                (dividends.index.date <= end_date)
            ]
            
            # Create DataFrame
            df = pd.DataFrame({
                "ex_date": dividends.index.date,
                "dividend_amount": dividends.values,
                "dividend_type": "regular",
                "data_source": self.name,
            })
            
            logger.info(f"Successfully fetched {len(df)} dividend records for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching dividends for {ticker}: {e}")
            return pd.DataFrame()

    def get_splits(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch stock split history from Yahoo Finance."""
        try:
            logger.info(f"Fetching splits for {ticker}")
            
            stock = yf.Ticker(ticker)
            splits = stock.splits
            
            if splits.empty:
                logger.info(f"No splits found for {ticker}")
                return pd.DataFrame()
            
            # Filter by date range
            splits = splits[
                (splits.index.date >= start_date) & 
                (splits.index.date <= end_date)
            ]
            
            # Create DataFrame
            df = pd.DataFrame({
                "split_date": splits.index.date,
                "split_ratio": splits.values,
                "split_type": "split",
                "data_source": self.name,
            })
            
            logger.info(f"Successfully fetched {len(df)} split records for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching splits for {ticker}: {e}")
            return pd.DataFrame()

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker exists on Yahoo Finance."""
        try:
            stock = yf.Ticker(ticker)
            # Try to get info to validate ticker exists
            info = stock.info
            return bool(info and "symbol" in info)
        except Exception as e:
            logger.warning(f"Ticker validation failed for {ticker}: {e}")
            return False

    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Get company information."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "country": info.get("country", "US"),
                "exchange": info.get("exchange", ""),
            }
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return {}


class EODHDProvider(DataProvider):
    """EODHD data provider (placeholder for future implementation)."""

    def __init__(self, api_key: str):
        self.name = "eodhd"
        self.api_key = api_key
        self.base_url = "https://eodhd.com/api"

    def get_daily_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch daily prices from EODHD."""
        # TODO: Implement EODHD API integration
        logger.info("EODHD provider not yet implemented")
        return pd.DataFrame()

    def get_dividends(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch dividends from EODHD."""
        # TODO: Implement EODHD API integration
        logger.info("EODHD provider not yet implemented")
        return pd.DataFrame()

    def get_splits(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch splits from EODHD."""
        # TODO: Implement EODHD API integration
        logger.info("EODHD provider not yet implemented")
        return pd.DataFrame()

    def validate_ticker(self, ticker: str) -> bool:
        """Validate ticker on EODHD."""
        # TODO: Implement EODHD API integration
        return False


def get_provider(provider_name: str, **kwargs) -> DataProvider:
    """Factory function to get data provider instance."""
    providers = {
        "yfinance": YahooFinanceProvider,
        "eodhd": EODHDProvider,
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    if provider_name.lower() == "eodhd":
        return provider_class(kwargs.get("api_key"))
    
    return provider_class()
