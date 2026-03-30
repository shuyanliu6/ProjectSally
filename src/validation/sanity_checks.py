"""Sanity checks and data anomaly detection."""

from typing import Dict, List
import pandas as pd
import numpy as np
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SanityChecker:
    """Performs sanity checks on market data to detect anomalies."""

    def __init__(
        self,
        price_drop_threshold: float = 0.9,
        volume_spike_threshold: float = 5.0,
    ):
        """
        Args:
            price_drop_threshold: Flag if absolute % change exceeds this (0.9 = 90%)
            volume_spike_threshold: Flag if volume is this many × the 20-day average
        """
        self.price_drop_threshold = price_drop_threshold
        self.volume_spike_threshold = volume_spike_threshold

        # FIX: was initialized as a list [] but generate_report() called
        # .items() on it as if it were a dict, causing an AttributeError.
        self.anomalies: Dict[str, Dict[str, List[str]]] = {}

    # ------------------------------------------------------------------
    # Public check methods
    # ------------------------------------------------------------------

    def check_daily_prices(self, df: pd.DataFrame, ticker: str) -> Dict[str, List[str]]:
        """
        Check daily price data for anomalies.

        Args:
            df: DataFrame with columns: date, open_price, high_price,
                low_price, close_price, volume
            ticker: Ticker symbol (used for logging and report storage)

        Returns:
            Dict mapping anomaly category → list of description strings
        """
        anomalies: Dict[str, List[str]] = {
            "missing_data": [],
            "price_gaps": [],
            "extreme_moves": [],
            "volume_spikes": [],
            "ohlc_violations": [],
            "negative_values": [],
        }

        if df.empty:
            logger.warning(f"Empty DataFrame passed for {ticker}")
            self.anomalies[ticker] = anomalies
            return anomalies

        df = df.sort_values("date").reset_index(drop=True)

        # 1. Gaps in trading days
        if len(df) > 1:
            date_diffs = pd.to_datetime(df["date"]).diff()
            suspicious = date_diffs[date_diffs > pd.Timedelta(days=3)]
            for idx in suspicious.index:
                anomalies["missing_data"].append(
                    f"Gap of {date_diffs.iloc[idx].days} days before {df.iloc[idx]['date']}"
                )

        # 2. Extreme price moves
        if len(df) > 1:
            pct_changes = df["close_price"].pct_change().abs()
            extreme = pct_changes[pct_changes > self.price_drop_threshold]
            for idx in extreme.index:
                anomalies["extreme_moves"].append(
                    f"Price move of {pct_changes.iloc[idx] * 100:.1f}% on {df.iloc[idx]['date']}"
                )

        # 3. Volume spikes
        if len(df) > 1:
            avg_vol = df["volume"].rolling(window=20, min_periods=1).mean()
            ratio = df["volume"] / avg_vol.replace(0, np.nan)
            spikes = ratio[ratio > self.volume_spike_threshold]
            for idx in spikes.index:
                anomalies["volume_spikes"].append(
                    f"Volume {ratio.iloc[idx]:.1f}× average on {df.iloc[idx]['date']}"
                )

        # 4. OHLC relationship violations
        bad = df[
            (df["high_price"] < df["low_price"])
            | (df["high_price"] < df["open_price"])
            | (df["high_price"] < df["close_price"])
            | (df["low_price"] > df["open_price"])
            | (df["low_price"] > df["close_price"])
        ]
        for _, row in bad.iterrows():
            anomalies["ohlc_violations"].append(
                f"OHLC violation on {row['date']}: "
                f"O={row['open_price']}, H={row['high_price']}, "
                f"L={row['low_price']}, C={row['close_price']}"
            )

        # 5. Negative values
        for col in ("open_price", "high_price", "low_price", "close_price", "volume"):
            neg_rows = df[df[col] < 0]
            for _, row in neg_rows.iterrows():
                anomalies["negative_values"].append(
                    f"Negative {col} ({row[col]}) on {row['date']}"
                )

        total = sum(len(v) for v in anomalies.values())
        if total:
            logger.warning(f"{ticker}: {total} anomaly(ies) detected")
            for category, items in anomalies.items():
                if items:
                    logger.warning(f"  {category}: {len(items)}")

        # Store for later report generation
        self.anomalies[ticker] = anomalies
        return anomalies

    def check_dividends(self, df: pd.DataFrame, ticker: str) -> Dict[str, List[str]]:
        """Check dividend data for anomalies."""
        anomalies: Dict[str, List[str]] = {
            "negative_dividends": [],
            "duplicate_dates": [],
        }

        if df.empty:
            return anomalies

        for _, row in df[df["dividend_amount"] < 0].iterrows():
            anomalies["negative_dividends"].append(
                f"Negative dividend on {row['ex_date']}: {row['dividend_amount']}"
            )

        for _, row in df[df.duplicated(subset=["ex_date"], keep=False)].iterrows():
            anomalies["duplicate_dates"].append(f"Duplicate ex_date: {row['ex_date']}")

        return anomalies

    def check_splits(self, df: pd.DataFrame, ticker: str) -> Dict[str, List[str]]:
        """Check split data for anomalies."""
        anomalies: Dict[str, List[str]] = {
            "invalid_ratios": [],
            "duplicate_dates": [],
        }

        if df.empty:
            return anomalies

        for _, row in df[df["split_ratio"] <= 0].iterrows():
            anomalies["invalid_ratios"].append(
                f"Invalid ratio on {row['split_date']}: {row['split_ratio']}"
            )

        for _, row in df[df.duplicated(subset=["split_date"], keep=False)].iterrows():
            anomalies["duplicate_dates"].append(f"Duplicate split_date: {row['split_date']}")

        return anomalies

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self) -> str:
        """
        Return a human-readable summary of all anomalies collected so far.

        FIX: self.anomalies was a list but this method called .items() on it
        as if it were a dict — that would raise AttributeError on the first
        call. It is now correctly initialized as a dict in __init__.
        """
        if not self.anomalies:
            return "No anomalies detected."

        lines = ["Data Anomaly Report", "=" * 50]
        for ticker, anomaly_dict in self.anomalies.items():
            has_issues = any(anomaly_dict.values())
            if not has_issues:
                continue
            lines.append(f"\n{ticker}:")
            for category, items in anomaly_dict.items():
                if items:
                    lines.append(f"  {category}: {len(items)} issue(s)")
                    for item in items[:5]:   # show first 5 examples per category
                        lines.append(f"    • {item}")
                    if len(items) > 5:
                        lines.append(f"    … and {len(items) - 5} more")

        return "\n".join(lines) if len(lines) > 2 else "No anomalies detected."
