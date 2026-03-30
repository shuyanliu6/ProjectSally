"""
ETL Pipeline orchestration for Project Sally.

Key fix: replaced row-by-row INSERT with bulk PostgreSQL upserts, which turns
~N queries per ticker into a single statement regardless of dataset size.
"""

from typing import List, Dict, Optional
from datetime import datetime, date
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.etl.data_providers import DataProvider, get_provider
from src.database.schema import (
    Asset, DailyPrice, Dividend, Split, Fundamental, MarketDataMetadata
)
from src.validation.sanity_checks import SanityChecker
from src.validation.pit_logic import PITValidator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataPipeline:
    """Orchestrates the complete ETL process."""

    def __init__(
        self,
        provider: DataProvider,
        session: Session,
        batch_size: int = 1000,
        enable_validation: bool = True,
    ):
        self.provider = provider
        self.session = session
        self.batch_size = batch_size
        self.enable_validation = enable_validation
        self.sanity_checker = SanityChecker() if enable_validation else None
        self.pit_validator = PITValidator()
        self.stats: Dict[str, int] = {
            "assets_created": 0,
            "assets_updated": 0,
            "prices_upserted": 0,
            "dividends_inserted": 0,
            "splits_inserted": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------------
    # Asset management
    # ------------------------------------------------------------------

    def ingest_asset(
        self,
        ticker: str,
        name: Optional[str] = None,
        asset_type: str = "stock",
        exchange: str = "NASDAQ",
        skip_validation: bool = False,
    ) -> Optional[Asset]:
        """
        Create or update an asset record.

        Args:
            ticker: Ticker symbol
            name: Company name (fetched from provider if omitted)
            asset_type: "stock", "etf", etc.
            exchange: Primary exchange
            skip_validation: When True, skip the provider round-trip ticker
                             check (useful when ingesting large universes where
                             you know the tickers are valid).

        Returns:
            Asset ORM object, or None on failure.
        """
        try:
            # FIX: validate_ticker() makes an HTTP call — skip it when the
            # caller already knows the ticker is valid to avoid 1 API call
            # per ticker on large universes.
            if not skip_validation and not self.provider.validate_ticker(ticker):
                logger.warning(f"Ticker validation failed: {ticker}")
                return None

            if not name:
                info = self.provider.get_company_info(ticker)
                name = info.get("name") or ticker

            existing = self.session.query(Asset).filter(Asset.ticker == ticker).first()

            if existing:
                existing.name = name
                existing.updated_at = datetime.utcnow()
                self.session.commit()
                self.stats["assets_updated"] += 1
                logger.info(f"Updated asset: {ticker}")
                return existing

            asset = Asset(
                ticker=ticker,
                name=name,
                asset_type=asset_type,
                exchange=exchange,
                country="US",
                currency="USD",
                is_active=True,
            )
            self.session.add(asset)
            self.session.commit()
            self.stats["assets_created"] += 1
            logger.info(f"Created asset: {ticker}")
            return asset

        except Exception as e:
            logger.error(f"Error ingesting asset {ticker}: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
            return None

    # ------------------------------------------------------------------
    # Daily prices
    # ------------------------------------------------------------------

    def ingest_daily_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        skip_validation: bool = False,
    ) -> int:
        """
        Fetch and upsert daily price data for one ticker.

        Returns number of rows upserted.
        """
        try:
            logger.info(f"Ingesting prices for {ticker} ({start_date} → {end_date})")

            asset = self.session.query(Asset).filter(Asset.ticker == ticker).first()
            if not asset:
                # skip_validation=True here because we're called after ingest_asset
                asset = self.ingest_asset(ticker, skip_validation=True)
                if not asset:
                    logger.error(f"Could not create asset for {ticker}")
                    return 0

            prices_df = self.provider.get_daily_prices(ticker, start_date, end_date)
            if prices_df.empty:
                logger.warning(f"No price data returned for {ticker}")
                return 0

            if self.enable_validation and not skip_validation:
                anomalies = self.sanity_checker.check_daily_prices(prices_df, ticker)
                if any(anomalies.values()):
                    logger.warning(f"Anomalies detected in {ticker} price data")
                    for k, v in anomalies.items():
                        if v:
                            logger.warning(f"  {k}: {len(v)} issue(s)")

            count = self._bulk_upsert_prices(asset.id, prices_df)
            self.stats["prices_upserted"] += count
            self._update_metadata(asset.id, "daily_prices", count)
            logger.info(f"Upserted {count} price records for {ticker}")
            return count

        except Exception as e:
            logger.error(f"Error ingesting prices for {ticker}: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
            return 0

    def _bulk_upsert_prices(self, asset_id: int, prices_df: pd.DataFrame) -> int:
        """
        Upsert an entire DataFrame of prices in one SQL statement.

        FIX: The original code issued one SELECT + one INSERT/UPDATE per row.
        For 10 years of daily data (~2,500 rows) that was ~2,500 round-trips.
        A single pg INSERT ... ON CONFLICT DO UPDATE handles any dataset size
        in one statement.
        """
        if prices_df.empty:
            return 0

        records = []
        for _, row in prices_df.iterrows():
            records.append({
                "asset_id": asset_id,
                "date": row["date"],
                "open_price": row["open_price"],
                "high_price": row["high_price"],
                "low_price": row["low_price"],
                "close_price": row["close_price"],
                "adj_close_price": row["adj_close_price"],
                "volume": int(row["volume"]),
                "is_adjusted": bool(row.get("is_adjusted", False)),
                "data_source": row["data_source"],
            })

        # Process in batches to stay within parameter limits
        total = 0
        for i in range(0, len(records), self.batch_size):
            batch = records[i : i + self.batch_size]
            stmt = pg_insert(DailyPrice).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["asset_id", "date"],
                set_={
                    "open_price": stmt.excluded.open_price,
                    "high_price": stmt.excluded.high_price,
                    "low_price": stmt.excluded.low_price,
                    "close_price": stmt.excluded.close_price,
                    "adj_close_price": stmt.excluded.adj_close_price,
                    "volume": stmt.excluded.volume,
                    "data_source": stmt.excluded.data_source,
                },
            )
            self.session.execute(stmt)
            self.session.commit()
            total += len(batch)
            logger.debug(f"Upserted batch of {len(batch)} price records (total so far: {total})")

        return total

    # ------------------------------------------------------------------
    # Dividends
    # ------------------------------------------------------------------

    def ingest_dividends(self, ticker: str, start_date: date, end_date: date) -> int:
        """Fetch and insert dividend records (skips existing ex_dates)."""
        try:
            logger.info(f"Ingesting dividends for {ticker}")

            asset = self.session.query(Asset).filter(Asset.ticker == ticker).first()
            if not asset:
                logger.warning(f"Asset not found for {ticker} — skipping dividends")
                return 0

            dividends_df = self.provider.get_dividends(ticker, start_date, end_date)
            if dividends_df.empty:
                logger.info(f"No dividends found for {ticker}")
                return 0

            if self.enable_validation:
                anomalies = self.sanity_checker.check_dividends(dividends_df, ticker)
                if any(anomalies.values()):
                    logger.warning(f"Anomalies detected in {ticker} dividend data")

            count = self._insert_dividends(asset.id, dividends_df)
            self.stats["dividends_inserted"] += count
            logger.info(f"Inserted {count} dividend records for {ticker}")
            return count

        except Exception as e:
            logger.error(f"Error ingesting dividends for {ticker}: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
            return 0

    def _insert_dividends(self, asset_id: int, df: pd.DataFrame) -> int:
        """Insert dividends, skipping any ex_dates that already exist."""
        # Fetch existing ex_dates in one query
        existing_dates = {
            r.ex_date
            for r in self.session.query(Dividend.ex_date)
            .filter(Dividend.asset_id == asset_id)
            .all()
        }

        new_records = []
        for _, row in df.iterrows():
            if row["ex_date"] not in existing_dates:
                new_records.append(Dividend(
                    asset_id=asset_id,
                    ex_date=row["ex_date"],
                    payment_date=row.get("payment_date"),
                    record_date=row.get("record_date"),
                    dividend_amount=row["dividend_amount"],
                    dividend_type=row.get("dividend_type", "regular"),
                    data_source=row["data_source"],
                ))

        if new_records:
            self.session.bulk_save_objects(new_records)
            self.session.commit()

        return len(new_records)

    # ------------------------------------------------------------------
    # Splits
    # ------------------------------------------------------------------

    def ingest_splits(self, ticker: str, start_date: date, end_date: date) -> int:
        """Fetch and insert split records (skips existing split_dates)."""
        try:
            logger.info(f"Ingesting splits for {ticker}")

            asset = self.session.query(Asset).filter(Asset.ticker == ticker).first()
            if not asset:
                logger.warning(f"Asset not found for {ticker} — skipping splits")
                return 0

            splits_df = self.provider.get_splits(ticker, start_date, end_date)
            if splits_df.empty:
                logger.info(f"No splits found for {ticker}")
                return 0

            if self.enable_validation:
                anomalies = self.sanity_checker.check_splits(splits_df, ticker)
                if any(anomalies.values()):
                    logger.warning(f"Anomalies detected in {ticker} split data")

            count = self._insert_splits(asset.id, splits_df)
            self.stats["splits_inserted"] += count
            logger.info(f"Inserted {count} split records for {ticker}")
            return count

        except Exception as e:
            logger.error(f"Error ingesting splits for {ticker}: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
            return 0

    def _insert_splits(self, asset_id: int, df: pd.DataFrame) -> int:
        """Insert splits, skipping any split_dates that already exist."""
        existing_dates = {
            r.split_date
            for r in self.session.query(Split.split_date)
            .filter(Split.asset_id == asset_id)
            .all()
        }

        new_records = []
        for _, row in df.iterrows():
            if row["split_date"] not in existing_dates:
                new_records.append(Split(
                    asset_id=asset_id,
                    split_date=row["split_date"],
                    split_ratio=row["split_ratio"],
                    split_type=row.get("split_type", "split"),
                    data_source=row["data_source"],
                ))

        if new_records:
            self.session.bulk_save_objects(new_records)
            self.session.commit()

        return len(new_records)

    # ------------------------------------------------------------------
    # Universe ingestion
    # ------------------------------------------------------------------

    def ingest_universe(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Dict[str, int]]:
        """
        Ingest all data for a list of tickers.

        Returns a dict of {ticker: {prices, dividends, splits}} counts.
        """
        logger.info(f"Starting universe ingestion for {len(tickers)} ticker(s)")

        results: Dict[str, Dict[str, int]] = {}
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"[{i}/{len(tickers)}] Processing {ticker}")
            results[ticker] = {
                "prices": self.ingest_daily_prices(ticker, start_date, end_date),
                "dividends": self.ingest_dividends(ticker, start_date, end_date),
                "splits": self.ingest_splits(ticker, start_date, end_date),
            }

        logger.info("Universe ingestion complete")
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_metadata(self, asset_id: int, data_type: str, record_count: int) -> None:
        """Upsert the market_data_metadata row for this asset + data_type."""
        try:
            metadata = (
                self.session.query(MarketDataMetadata)
                .filter(
                    and_(
                        MarketDataMetadata.asset_id == asset_id,
                        MarketDataMetadata.data_type == data_type,
                    )
                )
                .first()
            )

            now = datetime.utcnow()
            if metadata:
                metadata.last_update = now
                metadata.last_successful_update = now
                metadata.status = "success"
                metadata.record_count = record_count
                metadata.error_message = None
            else:
                self.session.add(MarketDataMetadata(
                    asset_id=asset_id,
                    data_type=data_type,
                    last_update=now,
                    last_successful_update=now,
                    data_source=self.provider.name,
                    status="success",
                    record_count=record_count,
                ))

            self.session.commit()

        except Exception as e:
            logger.error(f"Error updating metadata for asset {asset_id}: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Return pipeline run statistics."""
        return self.stats.copy()

    def print_stats(self) -> None:
        """Log pipeline statistics."""
        logger.info("=" * 60)
        logger.info("ETL Pipeline Statistics")
        logger.info("=" * 60)
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")
