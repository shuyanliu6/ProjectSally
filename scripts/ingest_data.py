#!/usr/bin/env python3
"""
Data ingestion script for Project Sally.

Fetches market data from providers and loads into database.

Usage:
    python scripts/ingest_data.py --ticker AAPL
    python scripts/ingest_data.py --tickers AAPL MSFT GOOGL
    python scripts/ingest_data.py --universe sp500 --start-date 2020-01-01
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.database.connection import SessionLocal
from src.etl.data_providers import get_provider
from src.etl.pipelines import DataPipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Common stock universes
UNIVERSES = {
    "sp500": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JNJ", "V",
        "WMT", "JPM", "PG", "MA", "HD", "DIS", "MCD", "NFLX", "ADBE", "CRM",
    ],
    "tech": [
        "AAPL", "MSFT", "GOOGL", "META", "NVDA", "TSLA", "ADBE", "NFLX", "INTC", "AMD",
    ],
    "finance": [
        "JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "COIN", "SOFI", "UPST",
    ],
    "etf": [
        "SPY", "QQQ", "IWM", "EEM", "GLD", "TLT", "VIX",
    ],
}


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest market data into Project Sally database"
    )

    parser.add_argument(
        "--ticker",
        type=str,
        help="Single ticker to ingest",
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Multiple tickers to ingest",
    )

    parser.add_argument(
        "--universe",
        type=str,
        choices=list(UNIVERSES.keys()),
        help=f"Predefined universe to ingest: {', '.join(UNIVERSES.keys())}",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        default="2015-01-01",
        help="Start date (YYYY-MM-DD)",
    )

    parser.add_argument(
        "--end-date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date (YYYY-MM-DD)",
    )

    parser.add_argument(
        "--provider",
        type=str,
        default="yfinance",
        choices=["yfinance", "eodhd"],
        help="Data provider",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip sanity checks",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for database inserts",
    )

    return parser.parse_args()


def parse_date(date_str: str) -> date:
    """Parse date string."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    """Main ingestion workflow."""
    args = parse_arguments()

    # Validate arguments
    if not any([args.ticker, args.tickers, args.universe]):
        logger.error("Must specify --ticker, --tickers, or --universe")
        return 1

    # Parse dates
    try:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date)
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Determine tickers to ingest
    if args.ticker:
        tickers = [args.ticker]
    elif args.tickers:
        tickers = args.tickers
    else:  # universe
        tickers = UNIVERSES[args.universe]

    logger.info("=" * 60)
    logger.info("Project Sally - Data Ingestion")
    logger.info("=" * 60)
    logger.info(f"Tickers: {', '.join(tickers)}")
    logger.info(f"Date Range: {start_date} to {end_date}")
    logger.info(f"Provider: {args.provider}")
    logger.info(f"Batch Size: {args.batch_size}")
    logger.info("=" * 60)

    try:
        # Initialize components
        config = get_config()
        session = SessionLocal()
        provider = get_provider(args.provider)
        pipeline = DataPipeline(
            provider=provider,
            session=session,
            batch_size=args.batch_size,
            enable_validation=not args.skip_validation,
        )

        # Run ingestion
        logger.info(f"Starting ingestion of {len(tickers)} ticker(s)...")
        results = pipeline.ingest_universe(tickers, start_date, end_date)

        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("Ingestion Results")
        logger.info("=" * 60)

        total_prices = 0
        total_dividends = 0
        total_splits = 0

        for ticker, counts in results.items():
            logger.info(f"\n{ticker}:")
            logger.info(f"  Prices: {counts['prices']}")
            logger.info(f"  Dividends: {counts['dividends']}")
            logger.info(f"  Splits: {counts['splits']}")

            total_prices += counts["prices"]
            total_dividends += counts["dividends"]
            total_splits += counts["splits"]

        logger.info("\n" + "=" * 60)
        logger.info("Total Summary")
        logger.info("=" * 60)
        logger.info(f"Total Price Records: {total_prices}")
        logger.info(f"Total Dividends: {total_dividends}")
        logger.info(f"Total Splits: {total_splits}")

        # Print pipeline stats
        pipeline.print_stats()

        logger.info("\n✓ Ingestion complete!")
        return 0

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return 1

    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
