"""Sumber data harga: MetaTrader 5 (utama) atau Yahoo Finance (fallback).

Data disimpan sebagai CSV di folder data/ supaya backtest bisa diulang offline.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

TF_MT5 = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16388, "D1": 16408}
TF_YF = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h", "D1": "1d"}


def csv_path(symbol: str, timeframe: str) -> Path:
    return DATA_DIR / f"{symbol}_{timeframe}.csv"


def load_csv(symbol: str, timeframe: str) -> pd.DataFrame | None:
    p = csv_path(symbol, timeframe)
    if not p.exists():
        return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    return df


def save_csv(df: pd.DataFrame, symbol: str, timeframe: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = csv_path(symbol, timeframe)
    df.to_csv(p)
    return p


def fetch_mt5(symbol: str, timeframe: str, n_bars: int = 50000) -> pd.DataFrame:
    """Ambil data dari terminal MetaTrader 5 (harus terinstall & login)."""
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError(f"Gagal konek MT5: {mt5.last_error()}")
    try:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Simbol {symbol} tidak tersedia di broker ini")
        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, n_bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Tidak dapat data: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")[["open", "high", "low", "close", "tick_volume"]]
        df = df.rename(columns={"tick_volume": "volume"})
        return df
    finally:
        mt5.shutdown()


def fetch_yfinance(yf_symbol: str, timeframe: str) -> pd.DataFrame:
    """Fallback: Yahoo Finance (intraday terbatas ~60 hari, cukup untuk uji pipeline)."""
    import yfinance as yf

    interval = TF_YF[timeframe]
    period = "60d" if interval.endswith(("m", "h")) else "10y"
    df = yf.download(yf_symbol, interval=interval, period=period,
                     progress=False, auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"Yahoo Finance tidak mengembalikan data untuk {yf_symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "time"
    return df


def get_data(cfg: dict, source: str = "auto") -> pd.DataFrame:
    """source: 'auto' | 'mt5' | 'yf' | 'csv'."""
    symbol, tf = cfg["symbol"], cfg["timeframe"]

    if source in ("auto", "csv"):
        cached = load_csv(symbol, tf)
        if cached is not None:
            print(f"[data] pakai cache CSV: {csv_path(symbol, tf)} ({len(cached)} bar)")
            return cached
        if source == "csv":
            raise FileNotFoundError(f"Belum ada cache: {csv_path(symbol, tf)}")

    if source in ("auto", "mt5"):
        try:
            df = fetch_mt5(symbol, tf)
            save_csv(df, symbol, tf)
            print(f"[data] dari MT5: {len(df)} bar")
            return df
        except Exception as e:
            if source == "mt5":
                raise
            print(f"[data] MT5 tidak tersedia ({e}), fallback ke Yahoo Finance...")

    df = fetch_yfinance(cfg["yf_symbol"], tf)
    save_csv(df, symbol, tf)
    print(f"[data] dari Yahoo Finance ({cfg['yf_symbol']}): {len(df)} bar")
    return df
