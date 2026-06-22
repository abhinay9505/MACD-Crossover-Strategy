import pandas as pd

df = pd.read_csv("eurusd_h1.csv")

# Remove Yahoo header rows
df = df.iloc[2:].copy()

# Rename columns
df.columns = [
    "Datetime",
    "Close",
    "High",
    "Low",
    "Open",
    "Volume"
]

# Convert datatypes
df["Datetime"] = pd.to_datetime(
    df["Datetime"],
    utc=True,
    errors="coerce"
)

numeric_cols = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col])

df.to_csv(
    "eurusd_h1_clean.csv",
    index=False
)

print(df.head())
print(df.shape)
print(df.dtypes)