"""Unduh harga close S&P 500 → satu data/prices.parquet (untuk app).

Konsolidasi ke 1 Parquet (bukan ratusan CSV) → hemat memori & cepat dimuat
(PRD v2.0 B3). Hanya kolom close, ~3,5 tahun terakhir (cukup untuk momentum
6 bulan + grafik 2 tahun).

Pakai: python scripts/fetch_prices.py
"""
import pandas as pd
import yfinance as yf

from _common import ROOT  # noqa: F401

from universe_sp500 import TICKERS

PARQUET = ROOT / "data" / "prices.parquet"
PERIOD = "4y"
KEEP_ROWS = 900   # ~3,5 tahun bursa
BENCHMARKS = ["SPY", "QQQ"]   # acuan indeks (PRD B5)

if __name__ == "__main__":
    universe = TICKERS + BENCHMARKS
    frames = []
    for i in range(0, len(universe), 100):
        batch = universe[i:i + 100]
        df = yf.download(batch, period=PERIOD, interval="1d", auto_adjust=True,
                         progress=False, threads=True)
        close = df["Close"] if "Close" in df.columns.get_level_values(0) else df
        if isinstance(close, pd.Series):
            close = close.to_frame()
        frames.append(close)
        print(f"batch {i // 100 + 1}: {close.shape[1]} ticker")

    prices = pd.concat(frames, axis=1)
    prices = prices.loc[:, ~prices.columns.duplicated()]
    prices = prices.dropna(how="all").tail(KEEP_ROWS)
    prices.index.name = "time"
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(PARQUET)

    n_ok = prices.notna().any().sum()
    print(f"\nTersimpan: {PARQUET}")
    print(f"{prices.shape[0]} hari × {n_ok} ticker (dari {len(universe)} diminta)")
    print(f"Periode: {prices.index[0].date()} s/d {prices.index[-1].date()}")
    miss = [t for t in universe if t not in prices.columns or prices[t].isna().all()]
    if miss:
        print(f"Gagal/kosong ({len(miss)}): {miss}")

    # kurs USD/IDR (konteks harga IDR di app) — disimpan terpisah
    try:
        fx = yf.download("IDR=X", period="5d", interval="1d",
                         progress=False)["Close"].dropna()
        rate = float(fx.iloc[-1].item() if hasattr(fx.iloc[-1], "item")
                     else fx.iloc[-1])
        (ROOT / "data" / "fx_usd_idr.txt").write_text(str(round(rate, 2)))
        print(f"Kurs USD/IDR: {rate:,.0f}")
    except Exception as e:
        print(f"Gagal ambil kurs USD/IDR: {e}")
