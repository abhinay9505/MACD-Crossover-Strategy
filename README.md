Objective
Implement the same trading strategy across three different frameworks (vectorbt, Nautilus Trader, and MetaTrader 5) and run a backtest in each.
This tests your ability to read documentation, adapt to different framework conventions, and produce working, reproducible code — using AI coding tools as you normally would.

The Strategy: MACD Crossover
- Calculate MACD using a fast EMA (12-period), slow EMA (26-period), and signal line (9-period EMA of MACD)
- Go long when the MACD line crosses above the signal line
- Exit/go flat (or go short, your choice — just state which) when the MACD line crosses below the signal line

Important: Write the MACD calculation yourself (EMAs and the MACD/signal line math) rather than using a built-in/library indicator function. This applies across all three implementations.

Asset & Timeframe
Use the same instrument and timeframe across all three platforms (e.g., EUR/USD on the 1-hour timeframe, or another liquid pair/timeframe of your choice — just state which and keep it consistent). Use the same date range for all three backtests as well.

Task
1. vectorbt
   - Pull or load historical price data
   - Implement your own MACD calculation (EMAs + MACD/signal line) and the crossover logic
   - Run a vectorized backtest
   - Output key performance metrics (total return, Sharpe ratio, max drawdown, number of trades)

2. Nautilus Trader
   - Implement the same strategy as a Nautilus strategy class, with your own MACD calculation (not the built-in indicator)
   - Run a backtest using Nautilus's backtest engine
   - Output the same performance metrics

3. MetaTrader 5
   - Implement the strategy as an MQL5 Expert Advisor, with your own MACD calculation rather than the built-in iMACD
   - Run the Strategy Tester (or equivalent) backtest
   - Provide the backtest report from MT5 (screenshot or exported report)
