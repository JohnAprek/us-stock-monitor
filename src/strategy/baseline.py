"""Strategi dasar rule-based: trend-following EMA + pullback RSI.

Long  : EMA fast > EMA slow (uptrend) DAN RSI cross naik melewati rsi_buy
Short : EMA fast < EMA slow (downtrend) DAN RSI cross turun melewati rsi_sell
"""
import pandas as pd


def generate_signals(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """Return Series berisi 1 (long), -1 (short), 0 (tidak ada sinyal)."""
    s = cfg["strategy"]
    sig = pd.Series(0, index=df.index, dtype=int)

    cross_up = (df["rsi"] > s["rsi_buy"]) & (df["rsi"].shift() <= s["rsi_buy"])
    cross_dn = (df["rsi"] < s["rsi_sell"]) & (df["rsi"].shift() >= s["rsi_sell"])

    uptrend = df["ema_fast"] > df["ema_slow"]
    downtrend = df["ema_fast"] < df["ema_slow"]

    sig[uptrend & cross_up] = 1
    sig[downtrend & cross_dn] = -1

    # buang sinyal saat indikator belum matang (awal data)
    sig[df["ema_slow"].isna() | df["atr"].isna()] = 0
    return sig
