#!/usr/bin/env python3
"""
Generate data quality reports for ingested data.

Usage:
    python scripts/generate_quality_report.py --ticker AAPL
    python scripts/generate_quality_report.py --all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import SessionLocal
from src.database.schema import Asset, DailyPrice, Dividend, Split
from src.utils.logger import get_logger
from sqlalchemy import func

logger = get_logger(__name__)


def generate_asset_report(session, ticker: str = None):
    """Generate report on assets in database."""
    logger.info("\n" + "=" * 60)
    logger.info("Asset Inventory Report")
    logger.info("=" * 60)

    query = session.query(Asset)
    if ticker:
        query = query.filter(Asset.ticker == ticker)

    assets = query.all()

    if not assets:
        logger.info("No assets found")
        return

    logger.info(f"Total Assets: {len(assets)}\n")

    for asset in assets:
        logger.info(f"Ticker: {asset.ticker}")
        logger.info(f"  Name: {asset.name}")
        logger.info(f"  Type: {asset.asset_type}")
        logger.info(f"  Exchange: {asset.exchange}")
        logger.info(f"  Active: {asset.is_active}")

        # Get data counts
        price_count = session.query(func.count(DailyPrice.id)).filter(
            DailyPrice.asset_id == asset.id
        ).scalar()

        dividend_count = session.query(func.count(Dividend.id)).filter(
            Dividend.asset_id == asset.id
        ).scalar()

        split_count = session.query(func.count(Split.id)).filter(
            Split.asset_id == asset.id
        ).scalar()

        logger.info(f"  Price Records: {price_count}")
        logger.info(f"  Dividends: {dividend_count}")
        logger.info(f"  Splits: {split_count}")

        # Get date range
        if price_count > 0:
            price_range = session.query(
                func.min(DailyPrice.date),
                func.max(DailyPrice.date)
            ).filter(DailyPrice.asset_id == asset.id).first()

            if price_range[0] and price_range[1]:
                logger.info(f"  Date Range: {price_range[0]} to {price_range[1]}")

        logger.info()


def generate_data_completeness_report(session, ticker: str = None):
    """Generate report on data completeness."""
    logger.info("\n" + "=" * 60)
    logger.info("Data Completeness Report")
    logger.info("=" * 60)

    query = session.query(Asset)
    if ticker:
        query = query.filter(Asset.ticker == ticker)

    assets = query.all()

    if not assets:
        logger.info("No assets found")
        return

    for asset in assets:
        price_count = session.query(func.count(DailyPrice.id)).filter(
            DailyPrice.asset_id == asset.id
        ).scalar()

        if price_count == 0:
            logger.info(f"{asset.ticker}: No price data")
            continue

        # Get date range
        price_range = session.query(
            func.min(DailyPrice.date),
            func.max(DailyPrice.date)
        ).filter(DailyPrice.asset_id == asset.id).first()

        start_date = price_range[0]
        end_date = price_range[1]

        # Calculate expected trading days (roughly 252 per year)
        days_span = (end_date - start_date).days
        years = days_span / 365.25
        expected_records = int(years * 252)

        completeness = (price_count / expected_records * 100) if expected_records > 0 else 0

        logger.info(f"{asset.ticker}:")
        logger.info(f"  Records: {price_count}")
        logger.info(f"  Expected: ~{expected_records}")
        logger.info(f"  Completeness: {completeness:.1f}%")
        logger.info(f"  Date Range: {start_date} to {end_date}")
        logger.info()


def generate_anomaly_report(session, ticker: str = None):
    """Generate report on potential data anomalies."""
    logger.info("\n" + "=" * 60)
    logger.info("Data Anomaly Report")
    logger.info("=" * 60)

    query = session.query(Asset)
    if ticker:
        query = query.filter(Asset.ticker == ticker)

    assets = query.all()

    if not assets:
        logger.info("No assets found")
        return

    for asset in assets:
        anomalies = []

        # Check for OHLC violations
        ohlc_violations = session.query(DailyPrice).filter(
            DailyPrice.asset_id == asset.id,
            (DailyPrice.high_price < DailyPrice.low_price) |
            (DailyPrice.high_price < DailyPrice.open_price) |
            (DailyPrice.high_price < DailyPrice.close_price)
        ).count()

        if ohlc_violations > 0:
            anomalies.append(f"OHLC violations: {ohlc_violations}")

        # Check for negative prices
        negative_prices = session.query(DailyPrice).filter(
            DailyPrice.asset_id == asset.id,
            DailyPrice.close_price <= 0
        ).count()

        if negative_prices > 0:
            anomalies.append(f"Negative prices: {negative_prices}")

        # Check for zero volume days
        zero_volume = session.query(DailyPrice).filter(
            DailyPrice.asset_id == asset.id,
            DailyPrice.volume == 0
        ).count()

        if zero_volume > 0:
            anomalies.append(f"Zero volume days: {zero_volume}")

        if anomalies:
            logger.info(f"{asset.ticker}:")
            for anomaly in anomalies:
                logger.info(f"  ⚠ {anomaly}")
            logger.info()
        else:
            logger.info(f"{asset.ticker}: ✓ No anomalies detected\n")


def generate_summary_report(session):
    """Generate overall database summary."""
    logger.info("\n" + "=" * 60)
    logger.info("Database Summary")
    logger.info("=" * 60)

    total_assets = session.query(func.count(Asset.id)).scalar()
    total_prices = session.query(func.count(DailyPrice.id)).scalar()
    total_dividends = session.query(func.count(Dividend.id)).scalar()
    total_splits = session.query(func.count(Split.id)).scalar()

    logger.info(f"Total Assets: {total_assets}")
    logger.info(f"Total Price Records: {total_prices}")
    logger.info(f"Total Dividends: {total_dividends}")
    logger.info(f"Total Splits: {total_splits}")

    # Get date range across all data
    if total_prices > 0:
        date_range = session.query(
            func.min(DailyPrice.date),
            func.max(DailyPrice.date)
        ).first()

        if date_range[0] and date_range[1]:
            logger.info(f"Date Range: {date_range[0]} to {date_range[1]}")


def main():
    """Main report generation workflow."""
    parser = argparse.ArgumentParser(description="Generate data quality reports")

    parser.add_argument(
        "--ticker",
        type=str,
        help="Specific ticker to report on",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all reports",
    )

    parser.add_argument(
        "--assets",
        action="store_true",
        help="Generate asset inventory report",
    )

    parser.add_argument(
        "--completeness",
        action="store_true",
        help="Generate data completeness report",
    )

    parser.add_argument(
        "--anomalies",
        action="store_true",
        help="Generate anomaly report",
    )

    args = parser.parse_args()

    # Default to all reports if no specific report requested
    if not any([args.all, args.assets, args.completeness, args.anomalies]):
        args.all = True

    try:
        session = SessionLocal()

        logger.info("=" * 60)
        logger.info("Project Sally - Data Quality Report")
        logger.info(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        # Generate summary
        generate_summary_report(session)

        # Generate requested reports
        if args.all or args.assets:
            generate_asset_report(session, args.ticker)

        if args.all or args.completeness:
            generate_data_completeness_report(session, args.ticker)

        if args.all or args.anomalies:
            generate_anomaly_report(session, args.ticker)

        logger.info("\n✓ Report generation complete!")
        return 0

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        return 1

    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
