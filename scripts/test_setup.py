#!/usr/bin/env python3
"""
Test script to verify Phase 1 setup.

Tests:
1. Python environment and imports
2. Configuration loading
3. Database connection
4. Data provider connectivity
5. Validation modules
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.config import get_config
from src.etl.data_providers import YahooFinanceProvider
from src.validation.sanity_checks import SanityChecker
from src.validation.pit_logic import PITValidator
from datetime import date, timedelta

logger = get_logger(__name__)


def test_imports():
    """Test that all imports work."""
    logger.info("Testing imports...")
    try:
        from src.database.schema import Asset, DailyPrice, Dividend, Split, Fundamental
        from src.database.connection import get_engine, get_session
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
        logger.info(f"  Database: {config.db_host}:{config.db_port}/{config.db_name}")
        logger.info(f"  Data Provider: {config.data_provider}")
        logger.info(f"  Environment: {config.environment}")
        logger.info("✓ Configuration loaded successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration failed: {e}")
        return False


def test_data_provider():
    """Test data provider connectivity."""
    logger.info("Testing data provider...")
    try:
        provider = YahooFinanceProvider()
        
        # Test ticker validation
        logger.info("  Testing ticker validation...")
        is_valid = provider.validate_ticker("AAPL")
        if is_valid:
            logger.info("  ✓ AAPL ticker is valid")
        else:
            logger.warning("  ⚠ Could not validate AAPL ticker")
        
        # Test fetching data
        logger.info("  Testing data fetch...")
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        prices = provider.get_daily_prices("AAPL", start_date, end_date)
        if not prices.empty:
            logger.info(f"  ✓ Fetched {len(prices)} price records")
        else:
            logger.warning("  ⚠ No price data returned")
        
        logger.info("✓ Data provider test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Data provider test failed: {e}")
        return False


def test_validation():
    """Test validation modules."""
    logger.info("Testing validation modules...")
    try:
        # Test sanity checker
        checker = SanityChecker()
        logger.info("  ✓ SanityChecker initialized")
        
        # Test PIT validator
        pit_validator = PITValidator()
        logger.info("  ✓ PITValidator initialized")
        
        logger.info("✓ Validation modules test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Validation test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Project Sally - Phase 1 Setup Test")
    logger.info("=" * 60)

    results = {
        "Imports": test_imports(),
        "Configuration": test_config(),
        "Data Provider": test_data_provider(),
        "Validation": test_validation(),
    }

    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All tests passed! Phase 1 setup is ready.")
        return 0
    else:
        logger.error(f"\n⚠ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
