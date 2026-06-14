"""Skor multi-faktor: value, quality, growth, momentum.

Tiap metrik diubah jadi z-score relatif terhadap universe (di-winsorize 2%
supaya outlier tidak mendominasi), dirata-rata per faktor, lalu komposit
berbobot. Skor tinggi = menarik menurut faktor tersebut.
"""
import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = {"value": 1.0, "quality": 1.0, "growth": 1.0, "momentum": 1.0}


def _z(s: pd.Series, invert: bool = False) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    s = s.clip(s.quantile(0.02), s.quantile(0.98))
    std = s.std()
    z = (s - s.mean()) / std if std and std > 0 else s * 0
    return -z if invert else z


def edgar_scores(snap: pd.DataFrame) -> pd.DataFrame:
    """Skor 4 varian PRD F4.3 dari snapshot panel point-in-time EDGAR.

    Definisi TERKUNCI per PRD — dipakai backtest (M4) dan aplikasi (M5)
    supaya ranking produksi identik dengan yang diuji.
    """
    out = pd.DataFrame(index=snap.index)
    out["value"] = pd.concat([_z(snap["earnings_yield"]), _z(snap["book_price"]),
                              _z(snap["fcf_yield"])], axis=1).mean(axis=1)
    out["quality"] = pd.concat([_z(snap["roe"]), _z(snap["op_margin"]),
                                _z(snap["net_margin"]),
                                _z(snap["debt_equity"], invert=True)],
                               axis=1).mean(axis=1)
    out["growth"] = pd.concat([_z(snap["rev_growth"]), _z(snap["ni_growth"])],
                              axis=1).mean(axis=1)
    out["komposit"] = out[["value", "quality", "growth"]].mean(axis=1)
    return out


def compute_scores(fund: pd.DataFrame, closes: pd.DataFrame | None = None,
                   weights: dict | None = None) -> pd.DataFrame:
    f = pd.DataFrame(index=fund.index)

    fcf_yield = pd.to_numeric(fund["freeCashflow"], errors="coerce") / \
        pd.to_numeric(fund["marketCap"], errors="coerce")
    f["value"] = pd.concat([
        _z(fund["forwardPE"], invert=True),
        _z(fund["enterpriseToEbitda"], invert=True),
        _z(fund["priceToBook"], invert=True),
        _z(fcf_yield),
    ], axis=1).mean(axis=1)

    f["quality"] = pd.concat([
        _z(fund["returnOnEquity"]),
        _z(fund["profitMargins"]),
        _z(fund["operatingMargins"]),
        _z(fund["debtToEquity"], invert=True),
    ], axis=1).mean(axis=1)

    f["growth"] = pd.concat([
        _z(fund["revenueGrowth"]),
        _z(fund["earningsGrowth"]),
    ], axis=1).mean(axis=1)

    if closes is not None and len(closes) > 130:
        mom = closes.iloc[-21] / closes.iloc[-126] - 1  # 6 bulan, skip 1 bulan
        f["momentum"] = _z(mom.reindex(fund.index))
    else:
        f["momentum"] = 0.0

    w = weights or DEFAULT_WEIGHTS
    total = sum(w.values()) or 1
    f["komposit"] = sum(f[k] * v for k, v in w.items()) / total
    f["rank"] = f["komposit"].rank(ascending=False).astype("Int64")
    return f.sort_values("komposit", ascending=False)
