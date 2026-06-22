# Nautilus Trader — MACD Crossover Strategy

## Files
- `macd_cross_strategy.py` — `ManualMacd` (hand-rolled EMA/MACD/signal, no
  built-in indicator) + `MACDCross` strategy class (long-only crossover
  logic) + `MACDCrossConfig`.
- `run_backtest.py` — sets up a simulated FX venue, loads EUR/USD H1 OHLCV
  bars from a CSV, runs the strategy through `BacktestEngine`, and prints/
  saves the same metrics as the vectorbt version.

## Running it

```bash
pip install -r requirements.txt
python run_backtest.py --data path/to/eurusd_h1.csv
python run_backtest.py --data path/to/eurusd_h1.xlsx --sheet Sheet1
```

`--data` accepts either a `.csv` or an `.xlsx`/`.xls`/`.xlsm` file. Both
are read directly with pandas (`pd.read_csv` / `pd.read_excel` -- no
other library involved) inside `load_bars()` in `run_backtest.py`. If
your Excel file has multiple sheets, pass `--sheet <name or index>` to
pick the one with your OHLCV data (defaults to the first sheet).

The file needs columns equivalent to:
`timestamp, open, high, low, close, volume`
(case-insensitive; `Datetime`/`Date` are accepted as aliases for
`timestamp`, matching yfinance's export convention. If there's no volume
column it's filled with 0 and then floored by `--min-volume`, see below.)

**Important — set `volume` to a large value (e.g. 1,000,000+) per bar**,
unless you have genuine tick-volume data. Nautilus's simulated matching
engine caps how much of an order can fill in a bar based on that bar's
`volume` field. I initially used small synthetic tick-count-style volume
values and saw orders fill for a tiny fraction of the requested size
(e.g. 34 units instead of 100,000) with no error — just silently low
fills. If your real EUR/USD data doesn't have meaningful volume (most FX
data doesn't), set it to something safely larger than your trade size
so it isn't the bottleneck, and note this assumption in your write-up.

## What I verified myself
- `ManualMacd`'s EMA/MACD/signal values match `pandas.Series.ewm(adjust=False)`
  exactly (0.0 absolute difference) on a synthetic price series — same
  check I ran on the vectorbt implementation, so both use identical math.
- Ran a full backtest end-to-end on synthetic EUR/USD H1 data through
  `BacktestEngine`: instrument/venue setup, bar ingestion via
  `BarDataWrangler`, strategy execution, and report generation all work
  (60 trades executed, account/fills/positions reports generated
  correctly).
- Hit and fixed the volume-capping issue described above myself while
  testing — documented it so you don't lose time on the same thing.

## Performance metrics
`run_backtest.py` prints and saves:
- Start/End balance, Total Return [%]
- Max Drawdown [%] (from the account equity curve)
- Sharpe Ratio (computed from per-bar equity returns — state your
  annualization convention in the README, e.g. multiply by sqrt(hours per
  year) if you want an annualized figure; I left it un-annualized and
  flagged this as a design choice)
- Number of Trades (closed positions)

Three CSVs are also saved for your write-up: `nautilus_account_report.csv`,
`nautilus_fills_report.csv`, `nautilus_positions_report.csv`.

## Author

Abhinay Rachakonda

Junior Python Developer Take-Home Assignment
