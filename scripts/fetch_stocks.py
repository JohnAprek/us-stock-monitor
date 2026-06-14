"""Unduh data harian ~110 saham besar US via Yahoo Finance (20 tahun).

Disimpan per ticker di data/stocks/. Catatan metodologis: daftar ticker
adalah konstituen besar SAAT INI -> ada survivorship bias yang akan
menggelembungkan hasil backtest. Diskon hasil 1-3%/tahun saat membaca.

Pakai: python scripts/fetch_stocks.py
"""
from pathlib import Path

import pandas as pd
import yfinance as yf

from _common import ROOT, load_config  # noqa: F401

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM",
    "JNJ", "V", "PG", "XOM", "UNH", "MA", "HD", "CVX", "MRK", "ABBV", "LLY",
    "PEP", "KO", "AVGO", "COST", "TMO", "WMT", "MCD", "CSCO", "ACN", "ABT",
    "CRM", "ADBE", "LIN", "DHR", "TXN", "NEE", "VZ", "CMCSA", "NKE", "PM",
    "ORCL", "WFC", "RTX", "HON", "UPS", "T", "IBM", "QCOM", "CAT", "SPGI",
    "INTC", "LOW", "INTU", "GS", "AMGN", "BA", "DE", "PFE", "BLK", "BKNG",
    "ELV", "MS", "AXP", "PLD", "MDT", "SBUX", "ADI", "BMY", "GILD", "ISRG",
    "CVS", "TJX", "MMC", "VRTX", "SYK", "C", "SCHW", "ZTS", "CB", "MO",
    "CI", "SO", "DUK", "BDX", "CL", "EOG", "ITW", "APD", "NOC", "CME",
    "EMR", "FDX", "SHW", "GD", "TGT", "ICE", "MCK", "USB", "PNC", "GM",
    "F", "AIG", "MET", "COF", "EL", "DOW", "BIIB", "DIS", "NFLX", "AMD",
    "PYPL", "UBER", "ABNB", "PLTR",
]

OUT = ROOT / "data" / "stocks"

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, []
    for i in range(0, len(TICKERS), 20):
        batch = TICKERS[i:i + 20]
        # auto_adjust=False: 'Close' = split-adjusted saja (untuk market cap
        # point-in-time), 'Adj Close' = total return (untuk return backtest).
        # actions=True: kolom 'Stock Splits' untuk faktor penyesuaian saham.
        df = yf.download(batch, period="20y", interval="1d",
                         group_by="ticker", auto_adjust=False,
                         actions=True, progress=False, threads=True)
        for t in batch:
            try:
                d = df[t].dropna(how="all")
            except KeyError:
                fail.append(t)
                continue
            if d.empty or len(d) < 500:
                fail.append(t)
                continue
            d.columns = [c.lower().replace(" ", "") for c in d.columns]
            d = d.rename(columns={"stocksplits": "splits"})
            d = d[[c for c in ("open", "high", "low", "close", "adjclose",
                               "volume", "splits") if c in d.columns]]
            d.index.name = "time"
            d.to_csv(OUT / f"{t}.csv")
            ok += 1
        print(f"batch {i // 20 + 1}: total tersimpan {ok}")
    print(f"\nSelesai: {ok} ticker tersimpan di {OUT}")
    if fail:
        print(f"Gagal: {fail}")
