"""Ambil data fundamental saham US via Yahoo Finance."""
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

FIELDS = [
    "shortName", "sector", "industry", "marketCap", "currentPrice",
    "trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda",
    "returnOnEquity", "profitMargins", "operatingMargins",
    "revenueGrowth", "earningsGrowth", "debtToEquity",
    "freeCashflow", "dividendYield", "beta",
    # harga & target analis (konteks — bukan penggerak skor)
    "targetMeanPrice", "targetHighPrice", "targetLowPrice", "targetMedianPrice",
    "numberOfAnalystOpinions", "recommendationKey", "recommendationMean",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fiftyDayAverage",
    "twoHundredDayAverage",
    # kalender laba (konteks) — tanggal rilis laporan berikutnya
    "earningsTimestamp", "earningsTimestampStart",
]


def fetch_fundamentals(tickers: list[str], out_path: Path,
                       pause: float = 0.3) -> pd.DataFrame:
    rows = {}
    for i, t in enumerate(tickers, 1):
        try:
            info = yf.Ticker(t).info
            rows[t] = {k: info.get(k) for k in FIELDS}
        except Exception as e:
            print(f"{t}: gagal ({e})")
        if i % 20 == 0:
            print(f"{i}/{len(tickers)} ticker...")
        time.sleep(pause)
    df = pd.DataFrame(rows).T
    df.index.name = "ticker"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path)
    return df


def load_fundamentals(path: Path) -> pd.DataFrame | None:
    if not Path(path).exists():
        return None
    return pd.read_csv(path, index_col=0)
