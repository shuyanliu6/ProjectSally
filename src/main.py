"""
Entry point for `python -m src`.

In development the container just idles so you can exec into it and run
scripts manually.  In production you could swap this out for a scheduler
or a specific ingestion command.
"""

import time
import logging

logger = logging.getLogger(__name__)


def main():
    logger.info("Project Sally container is running.")
    logger.info("Connect with:  docker-compose exec app bash")
    logger.info("Then run:      python scripts/init_db.py --create")

    # Keep the container alive so `docker-compose exec app bash` works.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()