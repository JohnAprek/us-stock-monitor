"""Strategi trend-following / momentum timeframe Daily.

Tiga aturan klasik yang sudah puluhan tahun terdokumentasi di riset
(pre-registered — parameternya standar literatur, BUKAN hasil optimasi kita,
untuk meminimalkan risiko curve-fitting):

1. donchian   : breakout 50 hari, exit di low/high 25 hari (gaya Turtle).
2. ema_trend  : selalu di pasar searah EMA50 vs EMA200 (golden/death cross).
3. tsmom      : time-series momentum 90 hari (long jika harga > 90 hari lalu).

Output: Series posisi harian -1 / 0 / +1 (keputusan di close hari itu,
dieksekusi return hari berikutnya oleh backtester — tanpa lookahead).
"""
import numpy as np
import pandas as pd


def donchian(close: pd.Series, n_entry: int = 50, n_exit: int = 25) -> pd.Series:
    hi = close.rolling(n_entry).max().shift(1)
    lo = close.rolling(n_entry).min().shift(1)
    ex_lo = close.rolling(n_exit).min().shift(1)
    ex_hi = close.rolling(n_exit).max().shift(1)

    pos, state = [], 0
    for c, h, l, xl, xh in zip(close, hi, lo, ex_lo, ex_hi):
        if state == 1 and c < xl:
            state = 0
        elif state == -1 and c > xh:
            state = 0
        if not np.isnan(h) and c > h:
            state = 1
        elif not np.isnan(l) and c < l:
            state = -1
        pos.append(state)
    return pd.Series(pos, index=close.index, dtype=float)


def ema_trend(close: pd.Series, fast: int = 50, slow: int = 200) -> pd.Series:
    f = close.ewm(span=fast, adjust=False).mean()
    s = close.ewm(span=slow, adjust=False).mean()
    pos = pd.Series(np.sign(f - s), index=close.index)
    pos[: slow] = 0  # tunggu indikator matang
    return pos


def tsmom(close: pd.Series, lookback: int = 90) -> pd.Series:
    pos = pd.Series(np.sign(close - close.shift(lookback)), index=close.index)
    return pos.fillna(0)


STRATEGIES = {"donchian": donchian, "ema_trend": ema_trend, "tsmom": tsmom}
