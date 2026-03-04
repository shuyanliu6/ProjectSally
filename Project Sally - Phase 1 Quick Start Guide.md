# Project Sally - Phase 1 Quick Start Guide

Get up and running with Project Sally in 5 minutes.

## Prerequisites

- Docker Desktop installed (Mac or Windows)
- Git (optional, for cloning)

## Step 1: Install Docker Desktop

**Mac:**
- Download: https://www.docker.com/products/docker-desktop
- Choose Apple Silicon or Intel version
- Launch Docker Desktop

**Windows:**
- Download: https://www.docker.com/products/docker-desktop
- Install and launch Docker Desktop

## Step 2: Navigate to Project

```bash
cd ~/StockPickingSystem
```

## Step 3: Start Services

```bash
docker-compose up -d
```

Wait for services to start (30-60 seconds).

## Step 4: Initialize Database

```bash
docker-compose exec app python scripts/init_db.py --create
```

Expected output: `✓ Database initialized successfully!`

## Step 5: Test Setup

```bash
docker-compose exec app python scripts/test_setup.py
```

Expected output: `🎉 All tests passed! Phase 1 setup is ready.`

## Step 6: Ingest Sample Data

```bash
# Ingest a single stock
docker-compose exec app python scripts/ingest_data.py --ticker AAPL

# Or ingest multiple stocks
docker-compose exec app python scripts/ingest_data.py --tickers AAPL MSFT GOOGL

# Or ingest a predefined universe
docker-compose exec app python scripts/ingest_data.py --universe tech
```

## Step 7: Generate Quality Report

```bash
docker-compose exec app python scripts/generate_quality_report.py
```

## Step 8: Connect to Database (Optional)

From your Mac/Windows terminal:

```bash
psql -h localhost -U stock_user -d stock_picking_system
```

Password: `secure_password_123`

Then query:
```sql
SELECT ticker, COUNT(*) as price_count FROM assets a 
JOIN daily_prices dp ON a.id = dp.asset_id 
GROUP BY ticker;
```

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Connect to app container
docker-compose exec app bash

# Stop services
docker-compose stop

# Start services again
docker-compose start

# Remove everything
docker-compose down -v
```

## Using Makefile (Easier)

If you prefer shorter commands:

```bash
# Start and initialize everything
make dev

# Connect to container
make docker-shell

# Initialize database
make db-init

# Run tests
make test

# Generate report
docker-compose exec app python scripts/generate_quality_report.py
```

## What Just Happened?

1. ✅ PostgreSQL + TimescaleDB running in Docker
2. ✅ Python environment with all dependencies
3. ✅ Database schema created (6 tables)
4. ✅ Sample stock data ingested
5. ✅ Data quality validated

## Next Steps

- **Explore data**: Query the database to see ingested data
- **Ingest more**: Add more tickers with `ingest_data.py`
- **Validate data**: Run quality reports
- **Move to Phase 2**: Build factor library (Week 7-12)

## Troubleshooting

**"Docker daemon is not running"**
- Open Docker Desktop application

**"Port 5432 already in use"**
- Edit `docker-compose.yml` and change port to 5433
- Update `.env` with `DB_PORT=5433`

**"Cannot connect to database"**
- Wait 30 seconds for database to start
- Check logs: `docker-compose logs database`

**"Permission denied"**
- Try: `sudo docker-compose up -d`

## Documentation

- **Full Setup Guide**: `DOCKER_SETUP.md`
- **Project Overview**: `README.md`
- **Phase 1 Progress**: `PHASE_1_PROGRESS.md`
- **Database Schema**: `src/database/schema.py`

## Support

For issues or questions:
1. Check the logs: `docker-compose logs`
2. Review the documentation
3. Verify Docker is running
4. Try resetting: `docker-compose down -v && docker-compose up -d`

---

**You're all set!** 🚀

Start ingesting data and building your quantitative stock picking system.
