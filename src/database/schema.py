"""
Database schema for Project Sally.

Tables:
- assets: Master list of stocks/securities
- daily_prices: OHLCV data (hypertable for time-series)
- dividends: Dividend history
- fundamentals: Company fundamentals (quarterly/annual)
- splits: Stock split history
- market_data_metadata: Metadata about data sources and updates
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Boolean, Text,
    ForeignKey, Index, UniqueConstraint, CheckConstraint, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Asset(Base):
    """Master table for assets (stocks, ETFs, etc.)."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(50), nullable=False)  # stock, etf, index, etc.
    exchange = Column(String(10), nullable=False)  # NYSE, NASDAQ, etc.
    country = Column(String(2), nullable=False, default="US")
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    currency = Column(String(3), nullable=False, default="USD")
    is_active = Column(Boolean, default=True, nullable=False)
    inception_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    daily_prices = relationship("DailyPrice", back_populates="asset", cascade="all, delete-orphan")
    dividends = relationship("Dividend", back_populates="asset", cascade="all, delete-orphan")
    fundamentals = relationship("Fundamental", back_populates="asset", cascade="all, delete-orphan")
    splits = relationship("Split", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ticker_active", "ticker", "is_active"),
        UniqueConstraint("ticker", "exchange", name="uq_ticker_exchange"),
    )

    def __repr__(self):
        return f"<Asset(ticker={self.ticker}, name={self.name})>"


class DailyPrice(Base):
    """
    Daily OHLCV data - optimized as TimescaleDB hypertable.
    
    This table will be converted to a hypertable for efficient time-series queries.
    """

    __tablename__ = "daily_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    adj_close_price = Column(Float, nullable=False)  # Adjusted for splits/dividends
    volume = Column(Integer, nullable=False)
    
    # Data quality flags
    is_adjusted = Column(Boolean, default=False, nullable=False)
    data_source = Column(String(50), nullable=False)  # yfinance, eodhd, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="daily_prices")

    __table_args__ = (
        Index("idx_asset_date", "asset_id", "date", unique=True),
        CheckConstraint("close_price > 0", name="ck_close_price_positive"),
        CheckConstraint("volume >= 0", name="ck_volume_non_negative"),
    )

    def __repr__(self):
        return f"<DailyPrice(asset_id={self.asset_id}, date={self.date}, close={self.close_price})>"


class Dividend(Base):
    """Dividend history for assets."""

    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    ex_date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=True)
    record_date = Column(Date, nullable=True)
    dividend_amount = Column(Float, nullable=False)
    dividend_type = Column(String(50), nullable=False)  # regular, special, etc.
    data_source = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="dividends")

    __table_args__ = (
        Index("idx_asset_ex_date", "asset_id", "ex_date"),
        CheckConstraint("dividend_amount >= 0", name="ck_dividend_positive"),
    )

    def __repr__(self):
        return f"<Dividend(asset_id={self.asset_id}, ex_date={self.ex_date}, amount={self.dividend_amount})>"


class Split(Base):
    """Stock split history."""

    __tablename__ = "splits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    split_date = Column(Date, nullable=False)
    split_ratio = Column(Float, nullable=False)  # e.g., 2 for 2:1 split
    split_type = Column(String(50), nullable=False)  # split, reverse_split
    data_source = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="splits")

    __table_args__ = (
        Index("idx_asset_split_date", "asset_id", "split_date"),
        CheckConstraint("split_ratio > 0", name="ck_split_ratio_positive"),
    )

    def __repr__(self):
        return f"<Split(asset_id={self.asset_id}, date={self.split_date}, ratio={self.split_ratio})>"


class Fundamental(Base):
    """Company fundamentals - quarterly and annual data."""

    __tablename__ = "fundamentals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    fiscal_date = Column(Date, nullable=False)  # End of fiscal period
    period_type = Column(String(10), nullable=False)  # Q1, Q2, Q3, Q4, FY
    
    # Income Statement
    revenue = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)
    
    # Balance Sheet
    total_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    shareholders_equity = Column(Float, nullable=True)
    
    # Ratios
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)  # Return on Equity
    debt_to_equity = Column(Float, nullable=True)
    
    data_source = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="fundamentals")

    __table_args__ = (
        Index("idx_asset_fiscal_date", "asset_id", "fiscal_date"),
        UniqueConstraint("asset_id", "fiscal_date", "period_type", name="uq_fundamental"),
    )

    def __repr__(self):
        return f"<Fundamental(asset_id={self.asset_id}, fiscal_date={self.fiscal_date})>"


class MarketDataMetadata(Base):
    """Metadata about data sources and update status."""

    __tablename__ = "market_data_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    data_type = Column(String(50), nullable=False)  # daily_prices, dividends, etc.
    last_update = Column(DateTime, nullable=True)
    last_successful_update = Column(DateTime, nullable=True)
    data_source = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, success, failed
    error_message = Column(Text, nullable=True)
    record_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_asset_data_type", "asset_id", "data_type"),
        UniqueConstraint("asset_id", "data_type", name="uq_metadata"),
    )

    def __repr__(self):
        return f"<MarketDataMetadata(asset_id={self.asset_id}, data_type={self.data_type})>"


# Event listener to create TimescaleDB hypertable for daily_prices
@event.listens_for(Base.metadata, "after_create")
def create_hypertable(target, connection, tables, **kw):
    """Convert daily_prices table to TimescaleDB hypertable after creation."""
    if any(t.name == "daily_prices" for t in tables):
        try:
            connection.execute(
                text("""
                    SELECT create_hypertable('daily_prices', by_range('date'), 
                    if_not_exists => TRUE);
                """)
            )
            print("✓ Created TimescaleDB hypertable for daily_prices")
        except Exception as e:
            print(f"Note: Could not create hypertable (may already exist): {e}")
