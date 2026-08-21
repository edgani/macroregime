"""Re-download the sample S&P 500 5yr OHLC panel (public GitHub) for run_research.py --all."""
import pandas as pd, urllib.request, io
URL = "https://raw.githubusercontent.com/plotly/datasets/master/all_stocks_5yr.csv"
print("downloading sample S&P500 5yr panel...")
raw = urllib.request.urlopen(URL, timeout=60).read()
df = pd.read_csv(io.BytesIO(raw), parse_dates=["date"])
g = df.groupby("Name").size(); keep = g[g >= 1000].index
df[df.Name.isin(keep)].to_parquet("research/sp500_panel.parquet")
print(f"saved research/sp500_panel.parquet ({len(keep)} tickers, {df.date.min().date()}→{df.date.max().date()})")
