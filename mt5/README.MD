# MetaTrader 5 MACD Crossover Strategy

## Overview

This project contains a MetaTrader 5 Expert Advisor (EA) implementing a MACD Crossover trading strategy using a custom MACD calculation instead of the built-in `iMACD` indicator.

The strategy was developed as part of a trading strategy backtesting assignment and tested using the MetaTrader 5 Strategy Tester.

---

## Strategy Description

### Indicator Parameters

| Parameter  | Value |
| ---------- | ----- |
| Fast EMA   | 12    |
| Slow EMA   | 26    |
| Signal EMA | 9     |

### MACD Formula

```text
MACD Line = EMA(12) - EMA(26)

Signal Line = EMA(MACD, 9)

Histogram = MACD Line - Signal Line
```

The MACD values are calculated manually inside the Expert Advisor.

---

## Trading Rules

### Buy Entry

Open a BUY position when:

```text
MACD[1] > Signal[1]
AND
MACD[2] <= Signal[2]
```

### Sell Entry

Open a SELL position when:

```text
MACD[1] < Signal[1]
AND
MACD[2] >= Signal[2]
```

### Position Management

* Only one position can remain active.
* Opposite positions are closed before opening a new trade.
* Signals are evaluated only on completed candles.

---

## Project Structure

```text
mt5/
│
├── MACD_Crossover.mq5
├── MACD_Crossover.ex5
│
├── reports/
│   ├── Mt5_report.pdf
│   ├── prebveiw.pdf
│   ├── Screenshot 2026-06-22 154206.png
│   └── template_name.tpl
│
└── Trade report-5052072436 2026-06-22 09-49.html
```

---

## Requirements

* MetaTrader 5
* EURUSD Historical Data
* H1 Timeframe

---

## Running the Backtest

1. Open MetaTrader 5.
2. Press `Ctrl + R` to open Strategy Tester.
3. Select:

```text
Expert Advisor : MACD_Crossover
Symbol         : EURUSD
Timeframe      : H1
Model          : Open Prices Only
Initial Deposit: 10000 USD
```

4. Click **Start**.

---

## Generated Reports

The following files contain the backtest results:

* Mt5_report.pdf
* Trade report HTML
* Strategy screenshots

These files can be used as supporting evidence for strategy evaluation and assignment submission.

---

## Performance Metrics

The Strategy Tester provides:

* Net Profit
* Gross Profit
* Gross Loss
* Profit Factor
* Expected Payoff
* Maximum Drawdown
* Total Trades
* Winning Percentage

---

## Notes

* The EA does not use the built-in `iMACD`.
* MACD calculations are implemented manually.
* Strategy is designed for educational and backtesting purposes.
* Results may vary depending on broker data, spread, and testing period.

---

## Author

Abhinay Rachakonda

Junior Python Developer Take-Home Assignment

MetaTrader 5 – MACD Crossover Strategy
