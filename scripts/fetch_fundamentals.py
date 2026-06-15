"""Ambil fundamental semua ticker universe saham.

Pakai: python scripts/fetch_fundamentals.py
"""
from _common import ROOT, load_config  # noqa: F401

from universe_sp500 import TICKERS

from src.stocks.fundamentals import fetch_fundamentals

if __name__ == "__main__":
    out = ROOT / "data" / "fundamentals.csv"
    df = fetch_fundamentals(TICKERS, out)
    print(f"\n{len(df)} ticker tersimpan: {out}")
