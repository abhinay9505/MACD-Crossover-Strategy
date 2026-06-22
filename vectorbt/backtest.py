import pandas as pd
import vectorbt as vbt

from signals import generate_signals


df = pd.read_csv(
    "../data/eurusd_h1_clean.csv"
)

df["Datetime"] = pd.to_datetime(
    df["Datetime"],
    utc=True
)

df.set_index(
    "Datetime",
    inplace=True
)

close = df["Close"]

entries, exits, macd, signal = (
    generate_signals(close)
)
portfolio = vbt.Portfolio.from_signals(
    close=close,
    entries=entries,
    exits=exits,
    init_cash=10000,
    fees=0.0001,
    slippage=0.0001,
    freq="1h"
)

# Set frequency so metrics that require it (Sharpe, Sortino, etc.) are computed
stats = portfolio.stats()

print(
    "\n===== RESULTS ====="
)

print(
    f"Total Return: "
    f"{stats['Total Return [%]']:.2f}%"
)

sharpe = stats.get('Sharpe Ratio')
if pd.isna(sharpe) or sharpe is None:
    sharpe_str = "N/A"
else:
    sharpe_str = f"{sharpe:.2f}"

print(
    f"Sharpe Ratio: "
    f"{sharpe_str}"
)

print(
    f"Max Drawdown: "
    f"{stats['Max Drawdown [%]']:.2f}%"
)

print(
    f"Trades: "
    f"{stats['Total Trades']}"
)

report = {
    "Framework": "VectorBT",
    "Total Return %": stats["Total Return [%]"],
    "Sharpe Ratio": stats["Sharpe Ratio"],
    "Max Drawdown %": stats["Max Drawdown [%]"],
    "Trades": stats["Total Trades"]
}

pd.DataFrame([report]).to_csv(
    "vectorbt_results.csv",
    index=False
)

fig = portfolio.plot()

fig.write_html(
    "vectorbt_report.html"
)