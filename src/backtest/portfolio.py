"""Backtester portofolio D1 berbasis posisi harian.

- pnl harian = posisi kemarin x return hari ini, dikurangi biaya tiap
  perubahan posisi (spread+komisi sebagai fraksi harga).
- Tiap simbol dinormalkan ke volatilitas target yang sama (vol targeting),
  supaya gold dan EURUSD menyumbang risiko setara di portofolio.
- Portofolio = rata-rata pnl semua simbol yang punya data hari itu.
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
TARGET_VOL = 0.10   # 10% per tahun per simbol
MAX_LEVERAGE = 4.0


def symbol_pnl(close: pd.Series, pos: pd.Series, cost_frac: float) -> pd.Series:
    ret = close.pct_change().fillna(0)

    # vol targeting: skala posisi dengan volatilitas 60 hari instrumen
    vol = ret.rolling(60).std() * np.sqrt(TRADING_DAYS)
    scale = (TARGET_VOL / vol).clip(upper=MAX_LEVERAGE).fillna(0)
    sized = (pos * scale).shift(1).fillna(0)

    turnover = sized.diff().abs().fillna(0)
    return sized * ret - turnover * cost_frac


def portfolio_pnl(pnls: dict) -> pd.Series:
    df = pd.DataFrame(pnls)
    return df.mean(axis=1, skipna=True).dropna()


def stats(pnl: pd.Series) -> dict:
    if len(pnl) < 30:
        return {"n_hari": len(pnl)}
    equity = (1 + pnl).cumprod()
    years = len(pnl) / TRADING_DAYS
    cagr = equity.iloc[-1] ** (1 / years) - 1
    ann_vol = pnl.std() * np.sqrt(TRADING_DAYS)
    sharpe = (pnl.mean() * TRADING_DAYS) / ann_vol if ann_vol > 0 else 0
    dd = (equity / equity.cummax() - 1).min()
    return {
        "tahun": round(years, 1),
        "cagr%": round(cagr * 100, 2),
        "sharpe": round(sharpe, 2),
        "maxdd%": round(dd * 100, 2),
        "vol%": round(ann_vol * 100, 1),
    }
