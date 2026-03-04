"""Sanity checks and data anomaly detection."""

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SanityChecker:
    """Performs sanity checks on market data to detect anomalies."""

    def __init__(self, price_drop_threshold: float = 0.9, volume_spike_threshold: float = 5.0):
        """
        Initialize sanity checker.
        
        Args:
            price_drop_threshold: Alert if price drops by this ratio (e.g., 0.9 = 90% drop)
            volume_spike_threshold: Alert if volume spikes by this multiple
        """
        self.price_drop_threshold = price_drop_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.anomalies = []

    def check_daily_prices(self, df: pd.DataFrame, ticker: str) -> Dict[str, List[str]]:
        """
        Check daily price data for anomalies.
        
        Args:
            df: DataFrame with columns: date, open_price, high_price, low_price, close_price, volume
            ticker: Stock ticker
            
        Returns:
            Dictionary of anomaly types and affected dates
        """
        anomalies = {
            "missing_data": [],
            "price_gaps": [],
            "extreme_drops": [],
            "volume_spikes": [],
            "ohlc_violations": [],
            "negative_values": [],
        }

        if df.empty:
            logger.warning(f"Empty DataFrame for {ticker}")
            return anomalies

        # Sort by date
        df = df.sort_values("date").reset_index(drop=True)

        # Check 1: Missing data points (gaps in trading days)
        if len(df) > 1:
            date_diffs = pd.to_datetime(df["date"]).diff()
            # Expected business day gap is 1 day, but can be 3 days on weekends
            suspicious_gaps = date_diffs[date_diffs > pd.Timedelta(days=3)]
            for idx in suspicious_gaps.index:
                anomalies["missing_data"].append(
                    f"Gap of {date_diffs.iloc[idx].days} days before {df.iloc[idx]['date']}"
                )

        # Check 2: Extreme price drops
        if len(df) > 1:
            price_changes = df["close_price"].pct_change().abs()
            extreme_drops = price_changes[price_changes > self.price_drop_threshold]
            for idx in extreme_drops.index:
                pct_change = price_changes.iloc[idx] * 100
                anomalies["extreme_drops"].append(
                    f"Price change of {pct_change:.1f}% on {df.iloc[idx]['date']}"
                )

        # Check 3: Volume spikes
        if len(df) > 1:
            avg_volume = df["volume"].rolling(window=20).mean()
            volume_ratio = df["volume"] / avg_volume
            spikes = volume_ratio[volume_ratio > self.volume_spike_threshold]
            for idx in spikes.index:
                anomalies["volume_spikes"].append(
                    f"Volume spike of {volume_ratio.iloc[idx]:.1f}x on {df.iloc[idx]['date']}"
                )

        # Check 4: OHLC violations (High < Low, etc.)
        ohlc_violations = df[
            (df["high_price"] < df["low_price"]) |
            (df["high_price"] < df["open_price"]) |
            (df["high_price"] < df["close_price"]) |
            (df["low_price"] > df["open_price"]) |
            (df["low_price"] > df["close_price"])
        ]
        for _, row in ohlc_violations.iterrows():
            anomalies["ohlc_violations"].append(
                f"OHLC violation on {row['date']}: O={row['open_price']}, "
                f"H={row['high_price']}, L={row['low_price']}, C={row['close_price']}"
            )

        # Check 5: Negative values
        negative_checks = [
            ("open_price", df[df["open_price"] < 0]),
            ("high_price", df[df["high_price"] < 0]),
            ("low_price", df[df["low_price"] < 0]),
            ("close_price", df[df["close_price"] < 0]),
            ("volume", df[df["volume"] < 0]),
        ]
        for col_name, neg_df in negative_checks:
            for _, row in neg_df.iterrows():
                anomalies["negative_values"].append(
                    f"Negative {col_name} on {row['date']}: {row[col_name]}"
                )

        # Log summary
        total_anomalies = sum(len(v) for v in anomalies.values())
        if total_anomalies > 0:
            logger.warning(f"Found {total_anomalies} anomalies for {ticker}")
            for anomaly_type, items in anomalies.items():
                if items:
                    logger.warning(f"  {anomaly_type}: {len(items)} issues")

        return anomalies

    def check_dividends(self, df: pd.DataFrame, ticker: str) -> Dict[str, List[str]]:
        """Check dividend data for anomalies."""
        anomalies = {
            "negative_dividends": [],
            "duplicate_dates": [],
        }

        if df.empty:
            return anomalies

        # Check for negative dividends
        negative = df[df["dividend_amount"] < 0]
        for _, row in negative.iterrows():
            anomalies["negative_dividends"].append(
                f"Negative dividend on {row['ex_date']}: {row['dividend_amount']}"
            )

        # Check for duplicate ex_dates
        duplicates = df[df.duplicated(subset=["ex_date"], keep=False)]
        for _, row in duplicates.iterrows():
            anomalies["duplicate_dates"].append(
                f"Duplicate ex_date: {row['ex_date']}"
            )

        return anomalies

    def check_splits(self, df: pd.DataFrame, ticker: str) -> Dict[str, List[str]]:
        """Check stock split data for anomalies."""
        anomalies = {
            "invalid_ratios": [],
            "duplicate_dates": [],
        }

        if df.empty:
            return anomalies

        # Check for invalid split ratios (should be > 0)
        invalid = df[df["split_ratio"] <= 0]
        for _, row in invalid.iterrows():
            anomalies["invalid_ratios"].append(
                f"Invalid split ratio on {row['split_date']}: {row['split_ratio']}"
            )

        # Check for duplicate split dates
        duplicates = df[df.duplicated(subset=["split_date"], keep=False)]
        for _, row in duplicates.iterrows():
            anomalies["duplicate_dates"].append(
                f"Duplicate split date: {row['split_date']}"
            )

        return anomalies

    def generate_report(self) -> str:
        """Generate a summary report of all anomalies found."""
        if not self.anomalies:
            return "No anomalies detected."

        report = "Data Anomaly Report\n"
        report += "=" * 50 + "\n"

        for ticker, anomaly_dict in self.anomalies.items():
            report += f"\n{ticker}:\n"
            for anomaly_type, items in anomaly_dict.items():
                if items:
                    report += f"  {anomaly_type}: {len(items)} issues\n"

        return report
