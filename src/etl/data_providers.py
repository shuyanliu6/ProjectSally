"""Data provider connectors for various sources."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import yfinance as yf
import pandas as pd
import requests
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


class MassiveDataProvider(DataProvider):
    """Massive.com API data provider."""

    def __init__(self, api_key: str, base_url: str = "https://api.massive.com"):
        self.name = "massive"
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        logger.info(f"Initialized Massive data provider with base URL: {base_url}")

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker exists."""
        try:
            # Try to fetch recent data to validate ticker
            today = datetime.now().date()
            five_days_ago = today - timedelta(days=5)
            
            url = (
                f"{self.base_url}/v2/aggs/ticker/{ticker}/range/1/day/"
                f"{five_days_ago.strftime('%Y-%m-%d')}/{today.strftime('%Y-%m-%d')}"
            )
            params = {"apiKey": self.api_key, "limit": 1}
            response = self.session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # Accept both OK and DELAYED status
                is_valid = data.get("status") in ["OK", "DELAYED"] and bool(data.get("results"))
                return is_valid
            return False
        except Exception as e:
            logger.warning(f"Ticker validation failed for {ticker}: {e}")
            return False

    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Get company information."""
        try:
            # Massive API doesn't have a direct company info endpoint
            # Return basic info with ticker as name
            return {"name": ticker}
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return {"name": ticker}

    def get_daily_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV data from Massive API."""
        try:
            logger.info(f"Fetching daily prices for {ticker} from {start_date} to {end_date}")
            
            # Construct the endpoint URL
            url = (
                f"{self.base_url}/v2/aggs/ticker/{ticker}/range/1/day/"
                f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            )
            
            params = {
                "apiKey": self.api_key,
                "adjusted": "true",
                "sort": "asc",
                "limit": 50000,
            }
            
            response = self.session.get(url, params=params, timeout=30)
            data = response.json()
            
            # Check for authorization errors
            if data.get("status") == "NOT_AUTHORIZED":
                logger.warning(
                    f"API authorization error for {ticker}: {data.get('message')}. "
                    f"Your plan may not include historical data access."
                )
                return pd.DataFrame()
            
            # Check for other errors
            if data.get("status") not in ["OK", "DELAYED"] or not data.get("results"):
                logger.info(f"No data found for {ticker} from {start_date} to {end_date}")
                return pd.DataFrame()
            
            all_bars = []
            for bar in data["results"]:
                # Convert millisecond timestamp to date
                timestamp_ms = bar.get("t", 0)
                bar_date = datetime.fromtimestamp(timestamp_ms / 1000).date()
                
                all_bars.append({
                    "date": bar_date,
                    "open_price": bar.get("o"),
                    "high_price": bar.get("h"),
                    "low_price": bar.get("l"),
                    "close_price": bar.get("c"),
                    "adj_close_price": bar.get("c"),  # Massive already adjusts
                    "volume": int(bar.get("v", 0)),
                    "is_adjusted": True,
                    "data_source": self.name,
                })
            
            df = pd.DataFrame(all_bars)
            logger.info(f"Successfully fetched {len(df)} records for {ticker} from Massive")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching daily prices for {ticker} from Massive: {e}")
            return pd.DataFrame()

    def get_splits(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch stock split history from Massive API."""
        try:
            logger.info(f"Fetching splits for {ticker}")
            
            url = f"{self.base_url}/v3/reference/splits"
            
            params = {
                "apiKey": self.api_key,
                "ticker": ticker,
                "limit": 1000,
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            splits = []
            if data.get("status") == "OK" and data.get("results"):
                for split in data["results"]:
                    split_date = split.get("execution_date")
                    
                    # Filter by date range
                    if split_date:
                        split_date_obj = datetime.strptime(split_date, "%Y-%m-%d").date()
                        if not (start_date <= split_date_obj <= end_date):
                            continue
                    
                    split_to = split.get("split_to", 1)
                    split_from = split.get("split_from", 1)
                    
                    splits.append({
                        "split_date": split_date,
                        "split_ratio": split_to / split_from,
                        "data_source": self.name,
                    })
            
            df = pd.DataFrame(splits) if splits else pd.DataFrame()
            logger.info(f"Successfully fetched {len(df)} split records for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching splits for {ticker} from Massive: {e}")
            return pd.DataFrame()

    def get_dividends(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch dividend history from Massive API."""
        try:
            logger.info(f"Fetching dividends for {ticker}")
            
            url = f"{self.base_url}/v3/reference/dividends"
            
            params = {
                "apiKey": self.api_key,
                "ticker": ticker,
                "limit": 1000,
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            dividends = []
            if data.get("status") == "OK" and data.get("results"):
                # Sort results by ex_dividend_date in descending order
                results = sorted(
                    data.get("results", []),
                    key=lambda x: x.get("ex_dividend_date", ""),
                    reverse=True
                )
                for div in results:
                    ex_date = div.get("ex_dividend_date")
                    
                    # Filter by date range
                    if ex_date:
                        ex_date_obj = datetime.strptime(ex_date, "%Y-%m-%d").date()
                        if not (start_date <= ex_date_obj <= end_date):
                            continue
                    
                    dividends.append({
                        "ex_date": ex_date,
                        "dividend_amount": float(div.get("cash_amount", 0)),
                        "dividend_type": div.get("dividend_type", "regular"),
                        "data_source": self.name,
                    })
            
            df = pd.DataFrame(dividends) if dividends else pd.DataFrame()
            logger.info(f"Successfully fetched {len(df)} dividend records for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching dividends for {ticker} from Massive: {e}")
            return pd.DataFrame()


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
    provider_name = provider_name.lower()
    
    if provider_name == "yfinance":
        return YahooFinanceProvider()
    
    elif provider_name == "massive":
        api_key = kwargs.get("api_key", "")
        base_url = kwargs.get("base_url", "https://api.massive.com")
        if not api_key:
            raise ValueError("Massive API key is required")
        return MassiveDataProvider(api_key=api_key, base_url=base_url)
    
    elif provider_name == "eodhd":
        api_key = kwargs.get("api_key", "")
        if not api_key:
            raise ValueError("EODHD API key is required")
        return EODHDProvider(api_key=api_key)
    
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
