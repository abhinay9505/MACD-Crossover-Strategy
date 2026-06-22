import yfinance as yf

df = yf.download(
    "EURUSD=X",
    start="2025-01-01",
    end="2026-01-01",
    interval="1h",

)

print(df.head())
print(df.shape)

df.to_csv("eurusd_h1.csv")