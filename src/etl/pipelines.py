"""
ETL Pipeline orchestration for Project Sally.

Handles data extraction, transformation, and loading into the database.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import insert, update, and_

from src.etl.data_providers import DataProvider, get_provider
from src.database.schema import Asset, DailyPrice, Dividend, Split, Fundamental, MarketDataMetadata
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
        batch_size: int = 100,
        enable_validation: bool = True,
    ):
        """
        Initialize data pipeline.

        Args:
            provider: Data provider instance
            session: SQLAlchemy session
            batch_size: Number of records to insert at once
            enable_validation: Whether to run sanity checks
        """
        self.provider = provider
        self.session = session
        self.batch_size = batch_size
        self.enable_validation = enable_validation
        self.sanity_checker = SanityChecker() if enable_validation else None
        self.pit_validator = PITValidator()
        self.stats = {
            "assets_created": 0,
            "assets_updated": 0,
            "prices_inserted": 0,
            "dividends_inserted": 0,
            "splits_inserted": 0,
            "errors": 0,
        }

    def ingest_asset(
        self,
        ticker: str,
        name: Optional[str] = None,
        asset_type: str = "stock",
        exchange: str = "NASDAQ",
    ) -> Optional[Asset]:
        """
        Create or update an asset in the database.

        Args:
            ticker: Stock ticker symbol
            name: Company name (fetched if not provided)
            asset_type: Type of asset (stock, etf, etc.)
            exchange: Exchange listing

        Returns:
            Asset object or None if failed
        """
        try:
            # Validate ticker with provider
            if not self.provider.validate_ticker(ticker):
                logger.warning(f"Ticker validation failed: {ticker}")
                return None

            # Fetch company info if name not provided
            if not name:
                info = self.provider.get_company_info(ticker)
                name = info.get("name", ticker)

            # Check if asset exists
            existing_asset = self.session.query(Asset).filter(
                Asset.ticker == ticker
            ).first()

            if existing_asset:
                # Update existing asset
                existing_asset.name = name
                existing_asset.updated_at = datetime.utcnow()
                self.session.commit()
                self.stats["assets_updated"] += 1
                logger.info(f"Updated asset: {ticker}")
                return existing_asset
            else:
                # Create new asset
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

    def ingest_daily_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        skip_validation: bool = False,
    ) -> int:
        """
        Ingest daily price data for a ticker.

        Args:
            ticker: Stock ticker
            start_date: Start date for data
            end_date: End date for data
            skip_validation: Skip sanity checks if True

        Returns:
            Number of records inserted
        """
        try:
            logger.info(f"Ingesting daily prices for {ticker} ({start_date} to {end_date})")

            # Get or create asset
            asset = self.session.query(Asset).filter(
                Asset.ticker == ticker
            ).first()

            if not asset:
                asset = self.ingest_asset(ticker)
                if not asset:
                    logger.error(f"Could not create asset for {ticker}")
                    return 0

            # Fetch price data
            prices_df = self.provider.get_daily_prices(ticker, start_date, end_date)

            if prices_df.empty:
                logger.warning(f"No price data returned for {ticker}")
                return 0

            # Run sanity checks
            if self.enable_validation and not skip_validation:
                anomalies = self.sanity_checker.check_daily_prices(prices_df, ticker)
                if any(anomalies.values()):
                    logger.warning(f"Found anomalies in {ticker} data:")
                    for anomaly_type, items in anomalies.items():
                        if items:
                            logger.warning(f"  {anomaly_type}: {len(items)} issues")

            # Prepare data for insertion
            records_inserted = 0
            for _, row in prices_df.iterrows():
                try:
                    # Check if record already exists
                    existing = self.session.query(DailyPrice).filter(
                        and_(
                            DailyPrice.asset_id == asset.id,
                            DailyPrice.date == row["date"],
                        )
                    ).first()

                    if existing:
                        # Update existing record
                        existing.open_price = row["open_price"]
                        existing.high_price = row["high_price"]
                        existing.low_price = row["low_price"]
                        existing.close_price = row["close_price"]
                        existing.adj_close_price = row["adj_close_price"]
                        existing.volume = row["volume"]
                        existing.data_source = row["data_source"]
                    else:
                        # Create new record
                        price = DailyPrice(
                            asset_id=asset.id,
                            date=row["date"],
                            open_price=row["open_price"],
                            high_price=row["high_price"],
                            low_price=row["low_price"],
                            close_price=row["close_price"],
                            adj_close_price=row["adj_close_price"],
                            volume=int(row["volume"]),
                            is_adjusted=row.get("is_adjusted", False),
                            data_source=row["data_source"],
                        )
                        self.session.add(price)

                    records_inserted += 1

                    # Batch commit
                    if records_inserted % self.batch_size == 0:
                        self.session.commit()
                        logger.debug(f"Committed {records_inserted} price records")

                except Exception as e:
                    logger.error(f"Error processing price record for {ticker}: {e}")
                    self.session.rollback()
                    self.stats["errors"] += 1

            # Final commit
            self.session.commit()
            self.stats["prices_inserted"] += records_inserted
            logger.info(f"Inserted {records_inserted} price records for {ticker}")

            # Update metadata
            self._update_metadata(asset.id, "daily_prices", records_inserted)

            return records_inserted

        except Exception as e:
            logger.error(f"Error ingesting daily prices for {ticker}: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
            return 0

    def ingest_dividends(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Ingest dividend data for a ticker.

        Args:
            ticker: Stock ticker
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Number of records inserted
        """
        try:
            logger.info(f"Ingesting dividends for {ticker}")

            # Get asset
            asset = self.session.query(Asset).filter(
                Asset.ticker == ticker
            ).first()

            if not asset:
                logger.warning(f"Asset not found for {ticker}")
                return 0

            # Fetch dividend data
            dividends_df = self.provider.get_dividends(ticker, start_date, end_date)

            if dividends_df.empty:
                logger.info(f"No dividends found for {ticker}")
                return 0

            # Run sanity checks
            if self.enable_validation:
                anomalies = self.sanity_checker.check_dividends(dividends_df, ticker)
                if any(anomalies.values()):
                    logger.warning(f"Found anomalies in {ticker} dividends")

            # Insert records
            records_inserted = 0
            for _, row in dividends_df.iterrows():
                try:
                    # Check if exists
                    existing = self.session.query(Dividend).filter(
                        and_(
                            Dividend.asset_id == asset.id,
                            Dividend.ex_date == row["ex_date"],
                        )
                    ).first()

                    if not existing:
                        dividend = Dividend(
                            asset_id=asset.id,
                            ex_date=row["ex_date"],
                            payment_date=row.get("payment_date"),
                            record_date=row.get("record_date"),
                            dividend_amount=row["dividend_amount"],
                            dividend_type=row.get("dividend_type", "regular"),
                            data_source=row["data_source"],
                        )
                        self.session.add(dividend)
                        records_inserted += 1

                        if records_inserted % self.batch_size == 0:
                            self.session.commit()

                except Exception as e:
                    logger.error(f"Error processing dividend for {ticker}: {e}")
                    self.stats["errors"] += 1

            self.session.commit()
            self.stats["dividends_inserted"] += records_inserted
            logger.info(f"Inserted {records_inserted} dividend records for {ticker}")

            return records_inserted

        except Exception as e:
            logger.error(f"Error ingesting dividends for {ticker}: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
            return 0

    def ingest_splits(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Ingest stock split data for a ticker.

        Args:
            ticker: Stock ticker
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Number of records inserted
        """
        try:
            logger.info(f"Ingesting splits for {ticker}")

            # Get asset
            asset = self.session.query(Asset).filter(
                Asset.ticker == ticker
            ).first()

            if not asset:
                logger.warning(f"Asset not found for {ticker}")
                return 0

            # Fetch split data
            splits_df = self.provider.get_splits(ticker, start_date, end_date)

            if splits_df.empty:
                logger.info(f"No splits found for {ticker}")
                return 0

            # Run sanity checks
            if self.enable_validation:
                anomalies = self.sanity_checker.check_splits(splits_df, ticker)
                if any(anomalies.values()):
                    logger.warning(f"Found anomalies in {ticker} splits")

            # Insert records
            records_inserted = 0
            for _, row in splits_df.iterrows():
                try:
                    # Check if exists
                    existing = self.session.query(Split).filter(
                        and_(
                            Split.asset_id == asset.id,
                            Split.split_date == row["split_date"],
                        )
                    ).first()

                    if not existing:
                        split = Split(
                            asset_id=asset.id,
                            split_date=row["split_date"],
                            split_ratio=row["split_ratio"],
                            split_type=row.get("split_type", "split"),
                            data_source=row["data_source"],
                        )
                        self.session.add(split)
                        records_inserted += 1

                        if records_inserted % self.batch_size == 0:
                            self.session.commit()

                except Exception as e:
                    logger.error(f"Error processing split for {ticker}: {e}")
                    self.stats["errors"] += 1

            self.session.commit()
            self.stats["splits_inserted"] += records_inserted
            logger.info(f"Inserted {records_inserted} split records for {ticker}")

            return records_inserted

        except Exception as e:
            logger.error(f"Error ingesting splits for {ticker}: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
            return 0

    def ingest_universe(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
    ) -> Dict[str, int]:
        """
        Ingest data for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting universe ingestion for {len(tickers)} tickers")

        results = {}
        for ticker in tickers:
            logger.info(f"Processing {ticker} ({tickers.index(ticker) + 1}/{len(tickers)})")

            # Ingest prices
            prices_count = self.ingest_daily_prices(ticker, start_date, end_date)

            # Ingest dividends
            dividends_count = self.ingest_dividends(ticker, start_date, end_date)

            # Ingest splits
            splits_count = self.ingest_splits(ticker, start_date, end_date)

            results[ticker] = {
                "prices": prices_count,
                "dividends": dividends_count,
                "splits": splits_count,
            }

        logger.info("Universe ingestion complete")
        return results

    def _update_metadata(
        self,
        asset_id: int,
        data_type: str,
        record_count: int,
    ) -> None:
        """Update metadata about data ingestion."""
        try:
            metadata = self.session.query(MarketDataMetadata).filter(
                and_(
                    MarketDataMetadata.asset_id == asset_id,
                    MarketDataMetadata.data_type == data_type,
                )
            ).first()

            if metadata:
                metadata.last_update = datetime.utcnow()
                metadata.last_successful_update = datetime.utcnow()
                metadata.status = "success"
                metadata.record_count = record_count
                metadata.error_message = None
            else:
                metadata = MarketDataMetadata(
                    asset_id=asset_id,
                    data_type=data_type,
                    last_update=datetime.utcnow(),
                    last_successful_update=datetime.utcnow(),
                    data_source=self.provider.name,
                    status="success",
                    record_count=record_count,
                )
                self.session.add(metadata)

            self.session.commit()

        except Exception as e:
            logger.error(f"Error updating metadata: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Get pipeline statistics."""
        return self.stats

    def print_stats(self) -> None:
        """Print pipeline statistics."""
        logger.info("=" * 60)
        logger.info("ETL Pipeline Statistics")
        logger.info("=" * 60)
        for key, value in self.stats.items():
            logger.info(f"{key}: {value}")
