#!/usr/bin/env python3
"""
Data ingestion script for Project Sally.

Fetches market data from providers and loads into database.

Usage:
    python scripts/ingest_data.py --ticker AAPL
    python scripts/ingest_data.py --tickers AAPL MSFT GOOGL
    python scripts/ingest_data.py --universe sp500 --start-date 2023-01-01
    python scripts/ingest_data.py --universe sp500 --resume   # skip already-ingested tickers
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.database.connection import SessionLocal
from src.database.schema import Asset, MarketDataMetadata
from src.etl.data_providers import get_provider
from src.etl.pipelines import DataPipeline
from src.utils.logger import get_logger
from sqlalchemy import and_

logger = get_logger(__name__)

# ── Universes ──────────────────────────────────────────────────────────────────

SP500 = [
    "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","A","APD","ABNB",
    "AKAM","ALB","ARE","ALGN","ALLE","LNT","ALL","GOOGL","GOOG","MO","AMZN",
    "AMCR","AEE","AAL","AEP","AXP","AIG","AMT","AWK","AMP","AME","AMGN","APH",
    "ADI","ANSS","AON","APA","AAPL","AMAT","APTV","ACGL","ADM","ANET","AJG",
    "AIZ","T","ATO","ADSK","ADP","AZO","AVB","AVY","AXON","BKR","BALL","BAC",
    "BK","BBWI","BAX","BDX","BRK.B","BBY","BIO","TECH","BIIB","BLK","BX","BA",
    "BCR","BMY","AVGO","BR","BRO","BF.B","BLDR","BXP","BSX","BMO","BLMN","CHRW",
    "CDNS","CZR","CPT","CPB","COF","CAH","KMX","CCL","CARR","CTLT","CAT","CBOE",
    "CBRE","CDW","CE","COR","CNC","CNX","CDAY","CF","CRL","SCHW","CHTR","CVX",
    "CMG","CB","CHD","CI","CINF","CTAS","CSCO","C","CFG","CLX","CME","CMS","KO",
    "CTSH","CL","CMCSA","CMA","CAG","COP","ED","STZ","CEG","COO","CPRT","GLW",
    "CPAY","CTVA","CSGP","COST","CTRA","CCI","CSX","CMI","CVS","DHR","DRI","DVA",
    "DAY","DE","DAL","DVN","DXCM","FANG","DLR","DFS","DG","DLTR","D","DPZ","DOV",
    "DOW","DHI","DTE","DUK","DD","EMN","ETN","EBAY","ECL","EIX","EW","EA","ELV",
    "EMR","ENPH","ETR","EOG","EPAM","EQT","EFX","EQIX","EQR","ESS","EL","ETSY",
    "EG","ES","EXC","EXPE","EXPD","EXR","XOM","FFIV","FDS","FICO","FAST","FRT",
    "FDX","FIS","FITB","FSLR","FE","FI","FMC","F","FTNT","FTV","FOXA","FOX",
    "BEN","FCX","GRMN","IT","GE","GEHC","GEV","GEN","GNRC","GD","GIS","GM","GPC",
    "GILD","GPN","GL","GDDY","GS","HAL","HIG","HAS","HCA","DOC","HSIC","HSY",
    "HES","HPE","HLT","HOLX","HD","HON","HRL","HST","HWM","HPQ","HUBB","HUM",
    "HBAN","HII","IBM","IEX","IDXX","ITW","INCY","IR","PODD","INTC","ICE","IFF",
    "IP","IPG","INTU","ISRG","IVZ","INVH","IQV","IRM","JKHY","J","JBL","JPM",
    "JNPR","K","KVUE","KDP","KEY","KEYS","KMB","KIM","KMI","KLAC","KHC","KR",
    "LHX","LH","LRCX","LW","LVS","LDOS","LEN","LLY","LIN","LYV","LKQ","LMT",
    "L","LOW","LULU","LYB","MTB","MRO","MPC","MKTX","MAR","MMC","MLM","MAS",
    "MA","MTCH","MKC","MCD","MCK","MDT","MRK","META","MET","MTD","MGM","MCHP",
    "MU","MSFT","MAA","MRNA","MHK","MOH","TAP","MDLZ","MPWR","MNST","MCO","MS",
    "MOS","MSI","MSCI","NDAQ","NTAP","NFLX","NEM","NWSA","NWS","NEE","NKE","NI",
    "NDSN","NSC","NTRS","NOC","NCLH","NRG","NUE","NVDA","NVR","NXPI","ORLY",
    "OXY","ODFL","OMC","ON","OKE","ORCL","OTIS","PCAR","PKG","PLTR","PANW",
    "PARA","PH","PAYX","PAYC","PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW",
    "PNC","POOL","PPG","PPL","PFG","PG","PGR","PLD","PRU","PEG","PTC","PSA",
    "PHM","PWR","QCOM","DGX","RL","RJF","RTX","O","REG","REGN","RF","RSG",
    "RMD","RVTY","ROK","ROL","ROP","ROST","RCL","SPGI","CRM","SBAC","SLB",
    "STX","SEE","SRE","NOW","SHW","SPG","SWKS","SJM","SNA","SOLV","SO","LUV",
    "SWK","SBUX","STT","STLD","STE","SYK","SYF","SNPS","SYY","TMUS","TROW",
    "TTWO","TPR","TRGP","TGT","TEL","TDY","TFX","TER","TSLA","TXN","TPL","TXT",
    "TMO","TJX","TSCO","TT","TDG","TRV","TRMB","TFC","TYL","TSN","USB","UBER",
    "UDR","ULTA","UNP","UAL","UPS","URI","UNH","UHS","VLO","VTR","VRSN","VRSK",
    "VZ","VRTX","VMC","WRB","GWW","WAB","WBA","WMT","DIS","WBD","WM","WAT",
    "WEC","WFC","WELL","WST","WDC","WY","WHR","WMB","WTW","WYNN","XEL","XYL",
    "YUM","ZBRA","ZBH","ZTS","VLTO",
]

UNIVERSES = {
    "sp500":   SP500,
    "tech":    ["AAPL","MSFT","GOOGL","META","NVDA","TSLA","ADBE","NFLX","INTC","AMD"],
    "finance": ["JPM","BAC","WFC","GS","MS","BLK","SCHW","COIN","SOFI","UPST"],
    "etf":     ["SPY","QQQ","IWM","EEM","GLD","TLT"],
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_arguments():
    parser = argparse.ArgumentParser(description="Ingest market data into Project Sally")

    parser.add_argument("--ticker",   type=str, help="Single ticker")
    parser.add_argument("--tickers",  nargs="+", help="Multiple tickers")
    parser.add_argument("--universe", type=str, choices=list(UNIVERSES.keys()))

    parser.add_argument("--start-date", type=str, default="2023-01-01")
    parser.add_argument("--end-date",   type=str,
                        default=datetime.now().strftime("%Y-%m-%d"))

    parser.add_argument("--provider", type=str, default="massive",
                        choices=["yfinance", "eodhd", "massive"])

    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--batch-size",      type=int, default=1000)

    # Rate limiting
    parser.add_argument("--delay",   type=float, default=0.5,
                        help="Seconds to wait between tickers (default 0.5)")
    parser.add_argument("--retries", type=int, default=3,
                        help="Retry attempts per ticker on failure (default 3)")

    # Resume support
    parser.add_argument("--resume", action="store_true",
                        help="Skip tickers that already have data in the DB")

    return parser.parse_args()


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {s}. Use YYYY-MM-DD")


def already_ingested(session, ticker: str, start_date: date) -> bool:
    """
    Return True if this ticker already has price data covering start_date.
    Used by --resume to skip tickers that completed in a previous run.
    """
    asset = session.query(Asset).filter(Asset.ticker == ticker).first()
    if not asset:
        return False
    meta = session.query(MarketDataMetadata).filter(
        and_(
            MarketDataMetadata.asset_id == asset.id,
            MarketDataMetadata.data_type == "daily_prices",
            MarketDataMetadata.status == "success",
        )
    ).first()
    return meta is not None


def ingest_with_retry(pipeline, ticker, start_date, end_date, retries, delay):
    """
    Attempt ingestion up to `retries` times with exponential back-off.
    Returns (prices, dividends, splits) counts or (0, 0, 0) on total failure.
    """
    for attempt in range(1, retries + 1):
        try:
            prices    = pipeline.ingest_daily_prices(ticker, start_date, end_date)
            dividends = pipeline.ingest_dividends(ticker, start_date, end_date)
            splits    = pipeline.ingest_splits(ticker, start_date, end_date)
            return prices, dividends, splits
        except Exception as e:
            wait = delay * (2 ** (attempt - 1))   # 0.5s, 1s, 2s …
            logger.warning(f"  Attempt {attempt}/{retries} failed for {ticker}: {e}")
            if attempt < retries:
                logger.info(f"  Retrying in {wait:.1f}s …")
                time.sleep(wait)
            else:
                logger.error(f"  All {retries} attempts failed for {ticker}")
                return 0, 0, 0


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    args = parse_arguments()

    if not any([args.ticker, args.tickers, args.universe]):
        logger.error("Must specify --ticker, --tickers, or --universe")
        return 1

    start_date = parse_date(args.start_date)
    end_date   = parse_date(args.end_date)

    if args.ticker:
        tickers = [args.ticker]
    elif args.tickers:
        tickers = args.tickers
    else:
        tickers = UNIVERSES[args.universe]

    config = get_config()

    provider_kwargs = {}
    if args.provider == "massive":
        if not config.massive_api_key:
            logger.error("MASSIVE_API_KEY not set in .env")
            return 1
        provider_kwargs = {
            "api_key":  config.massive_api_key,
            "base_url": config.massive_base_url,
        }
    elif args.provider == "eodhd":
        if not config.eodhd_api_key:
            logger.error("EODHD_API_KEY not set in .env")
            return 1
        provider_kwargs = {"api_key": config.eodhd_api_key}

    provider = get_provider(args.provider, **provider_kwargs)
    session  = SessionLocal()

    pipeline = DataPipeline(
        provider=provider,
        session=session,
        batch_size=args.batch_size,
        enable_validation=not args.skip_validation,
    )

    logger.info("=" * 60)
    logger.info("Project Sally — Data Ingestion")
    logger.info("=" * 60)
    logger.info(f"Universe:   {args.universe or 'custom'} ({len(tickers)} tickers)")
    logger.info(f"Date range: {start_date} → {end_date}")
    logger.info(f"Provider:   {args.provider}")
    logger.info(f"Delay:      {args.delay}s between tickers")
    logger.info(f"Retries:    {args.retries} per ticker")
    logger.info(f"Resume:     {args.resume}")
    logger.info("=" * 60)

    results    = {}
    skipped    = []
    failed     = []
    start_time = time.time()

    for i, ticker in enumerate(tickers, 1):

        # --resume: skip tickers that already completed
        if args.resume and already_ingested(session, ticker, start_date):
            logger.info(f"[{i}/{len(tickers)}] {ticker} — already ingested, skipping")
            skipped.append(ticker)
            continue

        logger.info(f"[{i}/{len(tickers)}] Processing {ticker} …")

        prices, dividends, splits = ingest_with_retry(
            pipeline, ticker, start_date, end_date,
            retries=args.retries,
            delay=args.delay,
        )

        results[ticker] = {"prices": prices, "dividends": dividends, "splits": splits}

        if prices == 0:
            failed.append(ticker)

        # Rate limit delay between tickers
        if i < len(tickers) and not (args.resume and already_ingested(session, ticker, start_date)):
            time.sleep(args.delay)

    elapsed = time.time() - start_time

    # ── Summary ──────────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("Ingestion Summary")
    logger.info("=" * 60)

    total_prices    = sum(v["prices"]    for v in results.values())
    total_dividends = sum(v["dividends"] for v in results.values())
    total_splits    = sum(v["splits"]    for v in results.values())

    logger.info(f"Tickers attempted: {len(tickers) - len(skipped)}")
    logger.info(f"Tickers skipped:   {len(skipped)}")
    logger.info(f"Tickers failed:    {len(failed)}")
    logger.info(f"Price records:     {total_prices:,}")
    logger.info(f"Dividends:         {total_dividends:,}")
    logger.info(f"Splits:            {total_splits:,}")
    logger.info(f"Elapsed:           {elapsed/60:.1f} min")

    if failed:
        logger.warning(f"\nFailed tickers ({len(failed)}):")
        logger.warning("  " + ", ".join(failed))
        logger.warning("\nRe-run with --resume to retry only failed tickers.")

    pipeline.print_stats()
    session.close()

    logger.info("\n✓ Ingestion complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())