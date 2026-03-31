# Project Sally — Roadmap

**Owner:** Shane Liu  
**Last Updated:** March 2026

---

## Philosophy

Build a working end-to-end quant system on a clean, liquid universe first.
Prove the alpha. Then scale the infrastructure.

---

## Current Status: MVP Build

### Data Universe
- **Tickers:** S&P 500 (~502 tickers)
- **History:** 2023-01-01 to present (2 years via Massive API)
- **Provider:** Massive API (free tier)
- **Rationale:** S&P 500 is the right MVP universe — liquid, well-understood,
  sufficient diversity across sectors. No point scaling to 5,000 tickers
  before factors are validated.

### Known Limitations (accepted for MVP)
- Survivorship bias — S&P 500 list reflects today's constituents, not
  historical membership. Companies that got delisted or removed are excluded.
- No fundamentals data yet (P/E, ROE etc.) — fundamentals table exists
  in schema but is unpopulated. Value factors deferred to post-MVP.
- Hardcoded ticker list in ingest_data.py — intentional for MVP simplicity.

---

## MVP Phases

### Phase 1 — Data Fortress ✅ COMPLETE
- PostgreSQL + TimescaleDB infrastructure
- ETL pipeline with bulk upsert (Massive API)
- Data validation: sanity checks + PIT logic
- Docker containerization
- S&P 500 ingested, 2 years of history

### Phase 2 — Factor Library (current)
- Momentum factors: returns, RSI, moving averages
- Volatility factors: realized vol, beta, drawdown
- Quality factors: deferred until fundamentals populated
- Value factors: deferred until fundamentals populated
- Compute on the fly (no pre-storage) for MVP

### Phase 3 — Backtesting Engine
- Event-driven backtester with realistic cost model
- Transaction costs, slippage, market impact
- PIT-correct data access (no look-ahead bias)
- Performance attribution

### Phase 4 — Portfolio Construction
- Mean-variance optimization
- Risk constraints (sector, position size)
- Factor exposure targets

### Phase 5 — Live Execution
- Paper trading first
- Broker API integration
- Risk monitoring and circuit breakers

---

## Production Scale (Post-MVP)

Once the full MVP pipeline is proven end-to-end:

### Universe Expansion
- Add `universe_members` table to schema (tracks historical index membership)
- Build `scripts/sync_universe.py` — pulls from Massive `/v3/reference/tickers`
- Covers full NYSE (~2,300) + NASDAQ (~3,300) = ~5,600 tickers
- Weekly sync to capture new listings and delistings
- Fixes survivorship bias with `added_date` / `removed_date` tracking

### Data Expansion
- Populate `fundamentals` table (quarterly earnings, balance sheet)
- Intraday data for execution-quality backtesting
- Alternative data (earnings call sentiment, options flow)

### Infrastructure Upgrades
- Automated daily ingestion scheduler (cron or Airflow)
- Pre-computed factor storage in DB (avoid recompute on every backtest)
- Connection pooling for production PostgreSQL
- Monitoring and alerting on data quality

### Factor Expansion
- Value factors: P/E, P/B, EV/EBITDA, dividend yield
- Quality factors: ROE, debt/equity, earnings stability, accruals
- Alternative factors: options implied vol, short interest, insider buying

---

## Key Technical Decisions Log

| Decision | Choice | Reason |
|----------|--------|--------|
| Universe for MVP | S&P 500 | Liquid, clean, sufficient for factor validation |
| Factor storage | Compute on the fly | Simpler for MVP; optimize in production |
| Data provider | Massive API | Already integrated, 2yr history on free tier |
| Ticker list | Hardcoded in ingest_data.py | MVP simplicity; DB-driven in production |
| Fundamentals | Deferred | Focus momentum + volatility factors first |
| Universe table | Deferred to production | Not needed until scaling beyond S&P 500 |

---

## Notes

> "Prove the alpha on a liquid, well-understood universe first.
>  There's no point building a 5,000-ticker pipeline if your
>  factors don't generate signal on 500." — design principle

The S&P 500 MVP is not a compromise — it's the correct first step.
Professional quant shops validate on liquid large-caps before scaling.