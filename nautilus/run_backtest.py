"""
Run the MACD crossover strategy through Nautilus Trader's BacktestEngine
(low-level API) on EUR/USD 1-hour bars, and print the same performance
metrics produced by the vectorbt implementation.

Usage:
    python run_backtest.py --data path/to/eurusd_h1.csv
    python run_backtest.py --data path/to/eurusd_h1.xlsx
    python run_backtest.py --data path/to/eurusd_h1.xlsx --sheet "Sheet1"

The file (CSV or Excel) is expected to have columns equivalent to:
    timestamp, open, high, low, close, volume
Column names are matched case-insensitively, and "Datetime" is accepted
as an alias for "timestamp" (yfinance's export convention). Both .csv and
.xlsx/.xls are read directly with pandas (`pd.read_csv` / `pd.read_excel`)
-- no other tooling required.

If you exported H1 EUR/USD data from MT5 (Strategy Tester > export, or
the MT5 History Center), reshape it into this format first.
"""

import argparse
import os
from decimal import Decimal

import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from macd_cross_strategy import MACDCross, MACDCrossConfig


def _normalize_bars(df: pd.DataFrame, min_volume: float) -> pd.DataFrame:
    """Shared cleanup applied after reading either a CSV or Excel file."""
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "datetime" in df.columns and "timestamp" not in df.columns:
        df = df.rename(columns={"datetime": "timestamp"})
    if "date" in df.columns and "timestamp" not in df.columns:
        df = df.rename(columns={"date": "timestamp"})

    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Data file is missing required column(s): {sorted(missing)}. "
            f"Found columns: {list(df.columns)}"
        )
    if "volume" not in df.columns:
        df["volume"] = 0.0

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    # Some bars can come through as duplicate or out-of-order timestamps
    # (e.g. yfinance occasionally emits a duplicate first row, or an Excel
    # sheet has a stray repeated header/row) -- Nautilus requires strictly
    # increasing timestamps.
    df = df[~df.index.duplicated(keep="first")]

    # IMPORTANT: Nautilus's simulated matching engine caps how much of an
    # order can fill in a bar based on that bar's `volume` field. Most real
    # FX OHLC data either has no genuine volume (tick volume only, often
    # tiny) or zero -- e.g. yfinance reports 0 volume for FX pairs -- which
    # silently throttles or blocks fills with no error: you just end up
    # with far fewer / smaller trades than expected, or zero trades. We
    # floor volume at `min_volume` so it is never the bottleneck for this
    # backtest. If your data source DOES have meaningful real volume you
    # trust, pass min_volume=0 to disable this override.
    if min_volume > 0:
        df["volume"] = df["volume"].clip(lower=min_volume)

    return df


def load_bars(path: str, sheet_name=0, min_volume: float = 10_000_000.0) -> pd.DataFrame:
    """
    Load EUR/USD H1 OHLCV bars from either a CSV or an Excel (.xlsx/.xls)
    file using pandas, and normalize into the format Nautilus needs.

    Parameters
    ----------
    path : str
        Path to the .csv, .xlsx, or .xls file.
    sheet_name : str | int, default 0
        Which sheet to read if `path` is an Excel file (ignored for CSV).
    min_volume : float
        Floor applied to volume so it never caps simulated order fills
        (see note below). Pass 0 to use the file's raw volume as-is.

    """
    ext = os.path.splitext(path)[1].lower()

    if ext in (".xlsx", ".xls", ".xlsm"):
        df = pd.read_excel(path, sheet_name=sheet_name)
    elif ext == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported file extension '{ext}'. Use .csv, .xlsx, .xls, or .xlsm")

    return _normalize_bars(df, min_volume=min_volume)


def main(
    data_path: str,
    trade_size: str = "100000",
    min_volume: float = 10_000_000.0,
    sheet_name=0,
) -> None:
    # ------------------------------------------------------------------
    # 1. Build the backtest engine
    # ------------------------------------------------------------------
    engine_config = BacktestEngineConfig(
        trader_id=TraderId("BACKTESTER-001"),
        logging=LoggingConfig(log_level="ERROR"),
    )
    engine = BacktestEngine(config=engine_config)

    # ------------------------------------------------------------------
    # 2. Add a simulated FX venue
    # ------------------------------------------------------------------
    SIM = Venue("SIM")
    engine.add_venue(
        venue=SIM,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(10_000, USD)],
    )

    # ------------------------------------------------------------------
    # 3. Add the instrument and historical bar data (CSV or Excel, read
    #    with pandas in load_bars() above)
    # ------------------------------------------------------------------
    EURUSD = TestInstrumentProvider.default_fx_ccy("EUR/USD", SIM)
    engine.add_instrument(EURUSD)

    bar_type = BarType.from_str("EUR/USD.SIM-1-HOUR-LAST-EXTERNAL")

    raw_bars = load_bars(data_path, sheet_name=sheet_name, min_volume=min_volume)
    print(f"Loaded {len(raw_bars)} bars from {data_path} "
          f"({raw_bars.index[0]} -> {raw_bars.index[-1]})")

    wrangler = BarDataWrangler(bar_type=bar_type, instrument=EURUSD)
    bars = wrangler.process(raw_bars)
    engine.add_data(bars)

    # ------------------------------------------------------------------
    # 4. Configure and add the strategy
    # ------------------------------------------------------------------
    strategy_config = MACDCrossConfig(
        instrument_id=EURUSD.id,
        bar_type=bar_type,
        trade_size=Decimal(trade_size),
        fast_ema_period=12,
        slow_ema_period=26,
        signal_ema_period=9,
    )
    strategy = MACDCross(config=strategy_config)
    engine.add_strategy(strategy=strategy)

    # ------------------------------------------------------------------
    # 5. Run
    # ------------------------------------------------------------------
    engine.run()

    # ------------------------------------------------------------------
    # 6. Metrics
    # ------------------------------------------------------------------
    print_metrics(engine, SIM)

    engine.dispose()


def print_metrics(engine: BacktestEngine, venue: Venue) -> None:
    account_report = engine.trader.generate_account_report(venue)
    fills_report = engine.trader.generate_order_fills_report()
    positions_report = engine.trader.generate_positions_report()

    print("\n================ NAUTILUS PERFORMANCE METRICS ================")

    if not account_report.empty:
        start_balance = float(account_report.iloc[0]["total"])
        end_balance = float(account_report.iloc[-1]["total"])
        total_return_pct = (end_balance / start_balance - 1.0) * 100
        print(f"Start Balance          : {start_balance:.2f}")
        print(f"End Balance             : {end_balance:.2f}")
        print(f"Total Return [%]        : {total_return_pct:.2f}")

        equity = account_report["total"].astype(float)
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        max_dd_pct = drawdown.min() * 100
        print(f"Max Drawdown [%]        : {max_dd_pct:.2f}")

        # Sharpe ratio computed from per-bar equity returns (not
        # annualized to a specific convention here -- state your
        # annualization assumption in the README).
        rets = equity.pct_change().dropna()
        if rets.std() != 0:
            sharpe = (rets.mean() / rets.std())
        else:
            sharpe = float("nan")
        print(f"Sharpe Ratio (per-bar)  : {sharpe:.3f}")
    else:
        print("No account history generated (no fills?).")

    n_trades = len(positions_report) if positions_report is not None else 0
    print(f"Number of Trades         : {n_trades}")
    print("================================================================\n")

    # Persist reports for the README
    account_report.to_csv("nautilus_account_report.csv")
    fills_report.to_csv("nautilus_fills_report.csv")
    positions_report.to_csv("nautilus_positions_report.csv")
    print("Saved: nautilus_account_report.csv, nautilus_fills_report.csv, nautilus_positions_report.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        required=True,
        help="Path to EUR/USD H1 OHLCV data file -- .csv or .xlsx/.xls (read with pandas)",
    )
    parser.add_argument(
        "--sheet",
        default=0,
        help="Sheet name or index to read if --data is an Excel file (default: first sheet)",
    )
    parser.add_argument("--trade-size", default="100000", help="Notional trade size per position")
    parser.add_argument(
        "--min-volume",
        type=float,
        default=10_000_000.0,
        help="Floor applied to each bar's volume so it never caps order fills "
        "(set to 0 to use your file's raw volume values as-is)",
    )
    args = parser.parse_args()

    # Allow --sheet to be either a string (sheet name) or int (sheet index)
    sheet = args.sheet
    if isinstance(sheet, str) and sheet.isdigit():
        sheet = int(sheet)

    main(args.data, args.trade_size, args.min_volume, sheet)