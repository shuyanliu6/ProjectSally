#!/usr/bin/env python3
"""
Initialize the database with schema and sample data.

Usage:
    python scripts/init_db.py --create    # Create all tables
    python scripts/init_db.py --drop      # Drop all tables (WARNING!)
    python scripts/init_db.py --reset     # Drop and recreate
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import init_db, drop_db
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Initialize Project Sally database")
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create all tables",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables (WARNING!)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables",
    )

    args = parser.parse_args()

    if args.reset:
        logger.info("Resetting database...")
        drop_db()
        init_db()
        logger.info("✓ Database reset complete")

    elif args.drop:
        confirm = input("Are you sure you want to drop all tables? (yes/no): ")
        if confirm.lower() == "yes":
            logger.info("Dropping database...")
            drop_db()
            logger.info("✓ Database dropped")
        else:
            logger.info("Operation cancelled")

    elif args.create:
        logger.info("Creating database...")
        init_db()
        logger.info("✓ Database created")

    else:
        # Default: create
        logger.info("Creating database...")
        init_db()
        logger.info("✓ Database created")


if __name__ == "__main__":
    main()
