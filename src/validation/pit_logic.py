"""
Point-in-Time (PIT) logic to prevent look-ahead bias.

PIT ensures that we only use data that would have been available at a specific point in time,
preventing the use of future information during backtesting.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PITValidator:
    """Ensures data respects Point-in-Time constraints."""

    def __init__(self, data_lag_days: int = 1):
        """
        Initialize PIT validator.
        
        Args:
            data_lag_days: Days of lag before data is considered "available"
                          (e.g., 1 day for T+1 settlement)
        """
        self.data_lag_days = data_lag_days

    def get_available_data_as_of(
        self,
        df: pd.DataFrame,
        as_of_date: date,
        data_column: str = "date",
    ) -> pd.DataFrame:
        """
        Get only data that would have been available as of a specific date.
        
        Args:
            df: DataFrame with a date column
            as_of_date: The date to check availability for
            data_column: Name of the date column
            
        Returns:
            Filtered DataFrame with only available data
        """
        # Data is available only after the lag period
        cutoff_date = as_of_date - timedelta(days=self.data_lag_days)
        
        available_data = df[pd.to_datetime(df[data_column]).dt.date <= cutoff_date]
        
        logger.debug(
            f"As of {as_of_date}: {len(available_data)} records available "
            f"(cutoff: {cutoff_date})"
        )
        
        return available_data

    def validate_backtest_data(
        self,
        prices_df: pd.DataFrame,
        backtest_start_date: date,
        backtest_end_date: date,
    ) -> bool:
        """
        Validate that backtest data doesn't have look-ahead bias.
        
        Args:
            prices_df: DataFrame with price data
            backtest_start_date: Start of backtest period
            backtest_end_date: End of backtest period
            
        Returns:
            True if data is valid, False if look-ahead bias detected
        """
        if prices_df.empty:
            logger.warning("Empty price DataFrame")
            return False

        prices_df = prices_df.copy()
        prices_df["date"] = pd.to_datetime(prices_df["date"]).dt.date

        # Check 1: No future data in backtest period
        future_data = prices_df[
            (prices_df["date"] >= backtest_start_date) &
            (prices_df["date"] <= backtest_end_date) &
            (prices_df["date"] > backtest_end_date)
        ]

        if not future_data.empty:
            logger.error(f"Found {len(future_data)} future data points in backtest period")
            return False

        # Check 2: Sufficient historical data before backtest
        historical_cutoff = backtest_start_date - timedelta(days=self.data_lag_days)
        historical_data = prices_df[prices_df["date"] < historical_cutoff]

        if len(historical_data) < 252:  # At least 1 year of trading data
            logger.warning(
                f"Only {len(historical_data)} historical records before backtest. "
                f"Recommend at least 252 (1 year)"
            )

        logger.info("Backtest data validation passed")
        return True

    def get_pit_snapshot(
        self,
        prices_df: pd.DataFrame,
        fundamentals_df: pd.DataFrame,
        snapshot_date: date,
    ) -> Dict[str, pd.DataFrame]:
        """
        Get a Point-in-Time snapshot of all data as of a specific date.
        
        Useful for factor calculations and portfolio construction.
        
        Args:
            prices_df: Daily price data
            fundamentals_df: Fundamental data
            snapshot_date: Date for the snapshot
            
        Returns:
            Dictionary with available prices and fundamentals as of that date
        """
        available_prices = self.get_available_data_as_of(
            prices_df,
            snapshot_date,
            data_column="date",
        )

        available_fundamentals = self.get_available_data_as_of(
            fundamentals_df,
            snapshot_date,
            data_column="fiscal_date",
        )

        return {
            "prices": available_prices,
            "fundamentals": available_fundamentals,
            "snapshot_date": snapshot_date,
        }

    def add_pit_metadata(
        self,
        df: pd.DataFrame,
        data_date_column: str = "date",
        pit_date_column: str = "pit_date",
    ) -> pd.DataFrame:
        """
        Add Point-in-Time metadata to a DataFrame.
        
        The PIT date is when the data became available (accounting for lag).
        
        Args:
            df: DataFrame to augment
            data_date_column: Name of the date column in the data
            pit_date_column: Name of the new PIT date column
            
        Returns:
            DataFrame with PIT metadata added
        """
        df = df.copy()
        df[data_date_column] = pd.to_datetime(df[data_date_column])
        df[pit_date_column] = df[data_date_column] + timedelta(days=self.data_lag_days)
        
        return df

    def detect_look_ahead_bias(
        self,
        factor_df: pd.DataFrame,
        price_df: pd.DataFrame,
        factor_date_column: str = "date",
        price_date_column: str = "date",
    ) -> List[str]:
        """
        Detect potential look-ahead bias in factor calculations.
        
        Returns list of issues found.
        
        Args:
            factor_df: DataFrame with calculated factors
            price_df: DataFrame with price data
            factor_date_column: Date column in factor data
            price_date_column: Date column in price data
            
        Returns:
            List of detected issues
        """
        issues = []

        factor_df = factor_df.copy()
        price_df = price_df.copy()

        factor_df[factor_date_column] = pd.to_datetime(factor_df[factor_date_column]).dt.date
        price_df[price_date_column] = pd.to_datetime(price_df[price_date_column]).dt.date

        # Check if factor dates are in the future relative to available price data
        for idx, row in factor_df.iterrows():
            factor_date = row[factor_date_column]
            
            # Get available price data as of factor date
            available_prices = price_df[
                price_df[price_date_column] <= factor_date - timedelta(days=self.data_lag_days)
            ]

            if available_prices.empty:
                issues.append(
                    f"Factor on {factor_date} has no available price data "
                    f"(accounting for {self.data_lag_days} day lag)"
                )

        if issues:
            logger.warning(f"Detected {len(issues)} potential look-ahead bias issues")

        return issues
