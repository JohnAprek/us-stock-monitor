"""Strategi breakout range Asia (untuk XAUUSD).

Ide: saat sesi Asia gold cenderung sideways membentuk range. Ketika London/NY
buka, harga sering breakout dari range itu. Kita ikut arah breakout pertama.

- Range Asia : high/low bar antara jam asia[0] s/d asia[1] (waktu server broker,
  IC Markets = GMT+2/+3, jadi Asia kira-kira jam 01-09).
- Entry      : bar pertama di jam entry[0] s/d entry[1] yang CLOSE menembus
  range. Hanya breakout pertama per hari (satu trade per hari maksimal).
- Filter tren opsional: long hanya jika EMA fast > EMA slow (proxy tren TF besar),
  short sebaliknya. Breakout yang melawan tren dilewati (hari itu hangus).
- Filter lebar range opsional: kalau range Asia sudah terlalu lebar relatif ATR,
  pergerakan dianggap sudah habis — skip hari itu.

SL/TP tetap berbasis ATR, dieksekusi oleh backtest engine / live runner.
"""
import pandas as pd


def generate_signals(df: pd.DataFrame, cfg: dict,
                     asia=(1, 9), entry=(10, 18),
                     trend_filter=True, max_range_atr=None,
                     trend_min=0.0) -> pd.Series:
    sig = pd.Series(0, index=df.index, dtype=int)

    for _, g in df.groupby(df.index.normalize()):
        h = g.index.hour
        asia_bars = g[(h >= asia[0]) & (h < asia[1])]
        if len(asia_bars) < 8:  # hari libur / data bolong
            continue
        hi = asia_bars["high"].max()
        lo = asia_bars["low"].min()

        win = g[(h >= entry[0]) & (h < entry[1])]
        if win.empty:
            continue
        if max_range_atr is not None:
            atr0 = win["atr"].iloc[0]
            if pd.isna(atr0) or (hi - lo) > max_range_atr * atr0:
                continue

        for t, row in win.iterrows():
            strength = row["trend_strength"]  # (EMA fast - slow) / ATR
            if row["close"] > hi:
                if not trend_filter or strength >= trend_min:
                    sig.loc[t] = 1
                break  # hanya breakout pertama per hari
            if row["close"] < lo:
                if not trend_filter or strength <= -trend_min:
                    sig.loc[t] = -1
                break

    sig[df["ema_slow"].isna() | df["atr"].isna()] = 0
    return sig
