# Project Sally: Industrial Quantitative Stock Picking System

A modular, institutional-standard system for alpha generation, portfolio construction, and execution.

**Owner:** Shane Liu  
**Timeline:** 24 Weeks (6 Months)  
**Status:** Phase 1 - The Data Fortress (In Progress)

## Project Overview

This system is designed to:
1. **Phase 1**: Build a "Golden Source" of survivorship-bias-free data
2. **Phase 2**: Create a modular factor library for quantitative signals
3. **Phase 3**: Implement rigorous backtesting with realistic cost models
4. **Phase 4**: Construct optimized portfolios with risk management
5. **Phase 5**: Deploy to production with live execution

## Phase 1: The Data Fortress (Weeks 1-6)

### Objectives
- Establish PostgreSQL + TimescaleDB infrastructure
- Design normalized schema for assets, prices, dividends, fundamentals
- Build ETL pipelines for data ingestion
- Implement data validation and Point-in-Time (PIT) logic

### Tasks
- [ ] **Week 1-2**: Schema & Storage
- [ ] **Week 3-4**: ETL Pipelines
- [ ] **Week 5-6**: Data Integrity & Validation

## Project Structure

```
StockPickingSystem/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.py
│
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py      # Database connection
│   │   ├── schema.py          # Schema definitions
│   │   └── migrations/        # Migration scripts
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── data_providers.py  # Data source connectors
│   │   ├── pipelines.py       # ETL pipeline logic
│   │   └── transformers.py    # Data transformations
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── sanity_checks.py   # Data anomaly detection
│   │   └── pit_logic.py       # Point-in-Time logic
│   └── utils/
│       ├── __init__.py
│       ├── logger.py          # Logging configuration
│       └── helpers.py         # Utility functions
│
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_etl.py
│   └── test_validation.py
│
└── scripts/
    ├── init_db.py             # Initialize database
    ├── migrate.py             # Run migrations
    └── seed_data.py           # Seed test data
```

## Setup Instructions

### 1. Prerequisites
- Python 3.9+
- PostgreSQL 13+
- TimescaleDB extension
- Git

### 2. Clone and Setup
```bash
cd ~/StockPickingSystem
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
# venv\Scripts\activate  # On Windows

pip install -r requirements.txt
```

### 3. Database Setup
```bash
# Create PostgreSQL database and enable TimescaleDB
psql -U postgres -f scripts/init_db.sql

# Run migrations
python scripts/migrate.py
```

### 4. Configuration
```bash
cp .env.example .env
# Edit .env with your settings
```

## Development Workflow

1. **Activate virtual environment**: `source venv/bin/activate`
2. **Run tests**: `pytest tests/`
3. **Check database**: `psql -d stock_picking_system`
4. **View logs**: `tail -f logs/app.log`

## Data Sources

### Current Implementation
- **Yahoo Finance** (via `yfinance`) - Free, reliable for US stocks

### Future Integration
- **EODHD** - Premium data quality
- **Polygon.io** - Comprehensive market data
- **Alpha Vantage** - Alternative data source

## Key Technologies

- **Database**: PostgreSQL + TimescaleDB (time-series optimization)
- **Python**: 3.9+ with type hints
- **ORM**: SQLAlchemy (for schema management)
- **Data**: Pandas, NumPy
- **Testing**: Pytest
- **Logging**: Python logging module

## Progress Tracking

See `PHASE_1_PROGRESS.md` for detailed task breakdown and status.

## Next Steps

1. ✅ Project structure setup
2. ⏳ PostgreSQL + TimescaleDB installation
3. ⏳ Database schema design
4. ⏳ Migration scripts
5. ⏳ ETL pipeline foundation

---

**Last Updated**: February 27, 2026  
**Current Phase**: 1 - The Data Fortress
