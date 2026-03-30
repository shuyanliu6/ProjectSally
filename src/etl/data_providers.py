"""Data provider connectors for various sources."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta

import yfinance as yf
import pandas as pd
import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataProvider(ABC):
    """Abstract base class for all data providers."""

    @abstractmethod
    def get_daily_prices(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch daily OHLCV data."""
        pass

    @abstractmethod
    def get_dividends(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch dividend history."""
        pass

    @abstractmethod
    def get_splits(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch stock split history."""
        pass

    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """Return True if the ticker exists on this provider."""
        pass

    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Return basic company metadata.
        Providers that don't support this return a minimal dict with the ticker as name.
        """
        return {"name": ticker}


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance data provider via the yfinance library."""

    def __init__(self):
        self.name = "yfinance"

    def get_daily_prices(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch daily OHLCV data from Yahoo Finance."""
        try:
            logger.info(f"Fetching daily prices for {ticker} from {start_date} to {end_date}")

            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False,
            )

            if data.empty:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            # FIX: newer yfinance versions return MultiIndex columns for single tickers.
            # Flatten to a regular Index so the rename below works reliably.
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            data = data.rename(columns={
                "Open": "open_price",
                "High": "high_price",
                "Low": "low_price",
                "Close": "close_price",
                "Adj Close": "adj_close_price",
                "Volume": "volume",
            })

            data = data.reset_index().rename(columns={"Date": "date"})
            data["date"] = pd.to_datetime(data["date"]).dt.date
            data["data_source"] = self.name
            data["is_adjusted"] = False

            logger.info(f"Fetched {len(data)} records for {ticker}")
            return data

        except Exception as e:
            logger.error(f"Error fetching daily prices for {ticker}: {e}")
            return pd.DataFrame()

    def get_dividends(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch dividend history from Yahoo Finance."""
        try:
            logger.info(f"Fetching dividends for {ticker}")

            stock = yf.Ticker(ticker)
            dividends = stock.dividends

            if dividends.empty:
                logger.info(f"No dividends found for {ticker}")
                return pd.DataFrame()

            dividends = dividends[
                (dividends.index.date >= start_date) &
                (dividends.index.date <= end_date)
            ]

            df = pd.DataFrame({
                "ex_date": dividends.index.date,
                "dividend_amount": dividends.values,
                "dividend_type": "regular",
                "data_source": self.name,
            })

            logger.info(f"Fetched {len(df)} dividend records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching dividends for {ticker}: {e}")
            return pd.DataFrame()

    def get_splits(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch stock split history from Yahoo Finance."""
        try:
            logger.info(f"Fetching splits for {ticker}")

            stock = yf.Ticker(ticker)
            splits = stock.splits

            if splits.empty:
                logger.info(f"No splits found for {ticker}")
                return pd.DataFrame()

            splits = splits[
                (splits.index.date >= start_date) &
                (splits.index.date <= end_date)
            ]

            df = pd.DataFrame({
                "split_date": splits.index.date,
                "split_ratio": splits.values,
                "split_type": "split",
                "data_source": self.name,
            })

            logger.info(f"Fetched {len(df)} split records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching splits for {ticker}: {e}")
            return pd.DataFrame()

    def validate_ticker(self, ticker: str) -> bool:
        """Return True if the ticker is known to Yahoo Finance."""
        try:
            info = yf.Ticker(ticker).info
            return bool(info and "symbol" in info)
        except Exception as e:
            logger.warning(f"Ticker validation failed for {ticker}: {e}")
            return False

    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Fetch company metadata from Yahoo Finance."""
        try:
            info = yf.Ticker(ticker).info
            return {
                "name": info.get("longName", ticker),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "country": info.get("country", "US"),
                "exchange": info.get("exchange", ""),
            }
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return {"name": ticker}


class MassiveDataProvider(DataProvider):
    """Massive.com API data provider."""

    def __init__(self, api_key: str, base_url: str = "https://api.massive.com"):
        self.name = "massive"
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        logger.info(f"Initialized Massive provider at {base_url}")

    def validate_ticker(self, ticker: str) -> bool:
        """Validate ticker by attempting a small recent fetch."""
        try:
            today = datetime.now().date()
            five_days_ago = today - timedelta(days=5)
            url = (
                f"{self.base_url}/v2/aggs/ticker/{ticker}/range/1/day/"
                f"{five_days_ago}/{today}"
            )
            response = self.session.get(url, params={"apiKey": self.api_key, "limit": 1}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") in ["OK", "DELAYED"] and bool(data.get("results"))
            return False
        except Exception as e:
            logger.warning(f"Ticker validation failed for {ticker}: {e}")
            return False

    def get_daily_prices(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch daily OHLCV data from Massive API."""
        try:
            logger.info(f"Fetching daily prices for {ticker} from {start_date} to {end_date}")

            url = (
                f"{self.base_url}/v2/aggs/ticker/{ticker}/range/1/day/"
                f"{start_date}/{end_date}"
            )
            params = {"apiKey": self.api_key, "adjusted": "true", "sort": "asc", "limit": 50000}
            response = self.session.get(url, params=params, timeout=30)
            data = response.json()

            if data.get("status") == "NOT_AUTHORIZED":
                logger.warning(f"Not authorized for {ticker}: {data.get('message')}")
                return pd.DataFrame()

            if data.get("status") not in ["OK", "DELAYED"] or not data.get("results"):
                logger.info(f"No data for {ticker} ({start_date} to {end_date})")
                return pd.DataFrame()

            rows = []
            for bar in data["results"]:
                bar_date = datetime.fromtimestamp(bar["t"] / 1000).date()
                rows.append({
                    "date": bar_date,
                    "open_price": bar.get("o"),
                    "high_price": bar.get("h"),
                    "low_price": bar.get("l"),
                    "close_price": bar.get("c"),
                    "adj_close_price": bar.get("c"),  # Massive pre-adjusts
                    "volume": int(bar.get("v", 0)),
                    "is_adjusted": True,
                    "data_source": self.name,
                })

            df = pd.DataFrame(rows)
            logger.info(f"Fetched {len(df)} records for {ticker} from Massive")
            return df

        except Exception as e:
            logger.error(f"Error fetching daily prices for {ticker} from Massive: {e}")
            return pd.DataFrame()

    def get_splits(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch stock split history from Massive API."""
        try:
            logger.info(f"Fetching splits for {ticker}")
            url = f"{self.base_url}/v3/reference/splits"
            response = self.session.get(
                url,
                params={"apiKey": self.api_key, "ticker": ticker, "limit": 1000},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            rows = []
            if data.get("status") == "OK" and data.get("results"):
                for split in data["results"]:
                    split_date_str = split.get("execution_date")
                    if not split_date_str:
                        continue
                    split_date_obj = datetime.strptime(split_date_str, "%Y-%m-%d").date()
                    if not (start_date <= split_date_obj <= end_date):
                        continue
                    rows.append({
                        "split_date": split_date_obj,
                        "split_ratio": split.get("split_to", 1) / split.get("split_from", 1),
                        "split_type": "split",
                        "data_source": self.name,
                    })

            df = pd.DataFrame(rows) if rows else pd.DataFrame()
            logger.info(f"Fetched {len(df)} split records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching splits for {ticker} from Massive: {e}")
            return pd.DataFrame()

    def get_dividends(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch dividend history from Massive API."""
        try:
            logger.info(f"Fetching dividends for {ticker}")
            url = f"{self.base_url}/v3/reference/dividends"
            response = self.session.get(
                url,
                params={"apiKey": self.api_key, "ticker": ticker, "limit": 1000},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            rows = []
            if data.get("status") == "OK" and data.get("results"):
                results = sorted(
                    data["results"],
                    key=lambda x: x.get("ex_dividend_date", ""),
                    reverse=True,
                )
                for div in results:
                    ex_date_str = div.get("ex_dividend_date")
                    if not ex_date_str:
                        continue
                    ex_date_obj = datetime.strptime(ex_date_str, "%Y-%m-%d").date()
                    if not (start_date <= ex_date_obj <= end_date):
                        continue
                    rows.append({
                        "ex_date": ex_date_obj,
                        "dividend_amount": float(div.get("cash_amount", 0)),
                        "dividend_type": div.get("dividend_type", "regular"),
                        "data_source": self.name,
                    })

            df = pd.DataFrame(rows) if rows else pd.DataFrame()
            logger.info(f"Fetched {len(df)} dividend records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching dividends for {ticker} from Massive: {e}")
            return pd.DataFrame()


class EODHDProvider(DataProvider):
    """EODHD data provider — placeholder for future implementation."""

    def __init__(self, api_key: str):
        self.name = "eodhd"
        self.api_key = api_key
        self.base_url = "https://eodhd.com/api"

    def get_daily_prices(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        logger.info("EODHD provider not yet implemented")
        return pd.DataFrame()

    def get_dividends(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        logger.info("EODHD provider not yet implemented")
        return pd.DataFrame()

    def get_splits(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        logger.info("EODHD provider not yet implemented")
        return pd.DataFrame()

    def validate_ticker(self, ticker: str) -> bool:
        return False


def get_provider(provider_name: str, **kwargs) -> DataProvider:
    """Factory — return the correct DataProvider for the given name."""
    name = provider_name.lower()

    if name == "yfinance":
        return YahooFinanceProvider()

    if name == "massive":
        api_key = kwargs.get("api_key", "")
        if not api_key:
            raise ValueError("Massive provider requires an api_key")
        return MassiveDataProvider(
            api_key=api_key,
            base_url=kwargs.get("base_url", "https://api.massive.com"),
        )

    if name == "eodhd":
        api_key = kwargs.get("api_key", "")
        if not api_key:
            raise ValueError("EODHD provider requires an api_key")
        return EODHDProvider(api_key=api_key)

    raise ValueError(f"Unknown provider: {provider_name!r}")
