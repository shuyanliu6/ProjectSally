#!/usr/bin/env python3
"""
Test script to verify Phase 1 setup.

Tests:
1. Python environment and imports
2. Configuration loading
3. Database connection
4. Data provider connectivity (uses whichever provider is configured)
5. Validation modules
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.config import get_config
from datetime import date, timedelta

logger = get_logger(__name__)


def test_imports():
    """Test that all imports work."""
    logger.info("Testing imports...")
    try:
        from src.database.schema import Asset, DailyPrice, Dividend, Split, Fundamental
        from src.database.connection import get_engine, get_db_session  # FIX: get_session removed
        from src.etl.data_providers import get_provider
        from src.etl.pipelines import DataPipeline
        from src.validation.sanity_checks import SanityChecker
        from src.validation.pit_logic import PITValidator
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    try:
        config = get_config()
        logger.info(f"  Database:      {config.db_host}:{config.db_port}/{config.db_name}")
        logger.info(f"  Data Provider: {config.data_provider}")
        logger.info(f"  Environment:   {config.environment}")
        logger.info("✓ Configuration loaded successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration failed: {e}")
        return False


def test_data_provider():
    """
    Test data provider connectivity.

    FIX: originally hardcoded YahooFinanceProvider() regardless of config.
    Now reads DATA_PROVIDER from the environment so it tests the provider
    you're actually using.
    """
    config = get_config()
    provider_name = config.data_provider
    logger.info(f"Testing data provider: {provider_name}")

    try:
        from src.etl.data_providers import get_provider

        # Build kwargs for providers that need an API key
        kwargs = {}
        if provider_name == "massive":
            if not config.massive_api_key:
                logger.error("  ✗ MASSIVE_API_KEY is not set in environment")
                return False
            kwargs = {"api_key": config.massive_api_key, "base_url": config.massive_base_url}
        elif provider_name == "eodhd":
            if not config.eodhd_api_key:
                logger.error("  ✗ EODHD_API_KEY is not set in environment")
                return False
            kwargs = {"api_key": config.eodhd_api_key}
        elif provider_name == "polygon":
            if not config.polygon_api_key:
                logger.error("  ✗ POLYGON_API_KEY is not set in environment")
                return False
            kwargs = {"api_key": config.polygon_api_key}

        provider = get_provider(provider_name, **kwargs)

        # Ticker validation
        logger.info("  Testing ticker validation...")
        is_valid = provider.validate_ticker("AAPL")
        if is_valid:
            logger.info("  ✓ AAPL ticker is valid")
        else:
            logger.warning("  ⚠ Could not validate AAPL ticker (may be a rate limit or plan issue)")

        # Data fetch
        logger.info("  Testing data fetch...")
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        prices = provider.get_daily_prices("AAPL", start_date, end_date)

        if not prices.empty:
            logger.info(f"  ✓ Fetched {len(prices)} price records")
        else:
            logger.warning("  ⚠ No price data returned (may be a plan/rate-limit issue)")

        logger.info(f"✓ Data provider test passed ({provider_name})")
        return True

    except Exception as e:
        logger.error(f"✗ Data provider test failed: {e}")
        return False


def test_database():
    """Test database connectivity."""
    logger.info("Testing database connection...")
    try:
        from src.database.connection import get_db_session
        from src.database.schema import Asset

        with get_db_session() as session:
            count = session.query(Asset).count()
            logger.info(f"  ✓ Connected — {count} asset(s) in database")

        logger.info("✓ Database connection test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def test_validation():
    """Test validation modules."""
    logger.info("Testing validation modules...")
    try:
        from src.validation.sanity_checks import SanityChecker
        from src.validation.pit_logic import PITValidator

        checker = SanityChecker()
        logger.info("  ✓ SanityChecker initialized")

        pit_validator = PITValidator()
        logger.info("  ✓ PITValidator initialized")

        logger.info("✓ Validation modules test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Validation test failed: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("Project Sally - Phase 1 Setup Test")
    logger.info("=" * 60)

    results = {
        "Imports":    test_imports(),
        "Config":     test_config(),
        "Database":   test_database(),
        "Provider":   test_data_provider(),
        "Validation": test_validation(),
    }

    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = sum(v for v in results.values())
    total = len(results)

    for name, result in results.items():
        logger.info(f"  {name}: {'✓ PASS' if result else '✗ FAIL'}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All tests passed! Phase 1 setup is ready.")
        return 0
    else:
        logger.error(f"\n⚠ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())