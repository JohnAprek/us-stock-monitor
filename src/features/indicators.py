"""Indikator teknikal + feature engineering untuk model ML."""
import numpy as np
import pandas as pd

FEATURE_COLS = [
    "rsi", "atr_pct", "ema_dist", "trend_strength",
    "ret_1", "ret_3", "ret_6", "ret_12",
    "hour", "dow",
]


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift()
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def add_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Tambah kolom indikator + fitur ML. Index harus DatetimeIndex."""
    s = cfg["strategy"]
    out = df.copy()
    out["ema_fast"] = ema(out["close"], s["ema_fast"])
    out["ema_slow"] = ema(out["close"], s["ema_slow"])
    out["rsi"] = rsi(out["close"], s["rsi_period"])
    out["atr"] = atr(out, 14)
    out["atr_pct"] = out["atr"] / out["close"]
    out["ema_dist"] = (out["close"] - out["ema_fast"]) / out["atr"]
    out["trend_strength"] = (out["ema_fast"] - out["ema_slow"]) / out["atr"]
    for k in (1, 3, 6, 12):
        out[f"ret_{k}"] = out["close"].pct_change(k)
    out["hour"] = out.index.hour
    out["dow"] = out.index.dayofweek
    return out
