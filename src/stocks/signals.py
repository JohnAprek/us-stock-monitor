"""Skor rekomendasi saham — gabungan 2 sinyal yang dipakai proyek ini:
momentum harga (6 bulan) + growth fundamental (pertumbuhan revenue & laba).

Output: tabel saham terurut, dengan label rekomendasi yang mudah dibaca.
Tidak ada backtest di sini — ini lapisan tampilan/pemeringkatan untuk app.
"""
import numpy as np
import pandas as pd

from src.stocks.scoring import _z, edgar_scores

# ambang label berdasarkan skor-z gabungan (relatif terhadap universe)
LABELS = [
    (1.0, "⭐ Sangat Direkomendasikan"),
    (0.3, "✅ Direkomendasikan"),
    (-0.3, "➖ Netral"),
    (-99, "⚠️ Kurang Menarik"),
]


def momentum_score(closes: pd.DataFrame, asof: pd.Timestamp | None = None) -> pd.Series:
    """Momentum 6 bulan, lewati 1 bulan terakhir (harga t-21d / t-126d)."""
    px = closes if asof is None else closes.loc[:asof]
    if len(px) < 130:
        return pd.Series(dtype=float)
    return (px.iloc[-21] / px.iloc[-126] - 1).dropna()


def label_for(z: float) -> str:
    for thresh, name in LABELS:
        if z >= thresh:
            return name
    return LABELS[-1][1]


def compute_returns(closes: pd.DataFrame) -> pd.DataFrame:
    """Return harga per ticker untuk beberapa horizon (kolom = ret_1B, dst)."""
    periods = {"ret_1B": 21, "ret_3B": 63, "ret_6B": 126, "ret_1Th": 252}
    last = closes.iloc[-1]
    out = {}
    for name, d in periods.items():
        if len(closes) > d:
            out[name] = last / closes.iloc[-1 - d] - 1
    return pd.DataFrame(out)


def recommend(panel, closes: pd.DataFrame,
              fund: pd.DataFrame | None = None,
              w_momentum: float = 1.0, w_growth: float = 1.0,
              asof: pd.Timestamp | None = None) -> pd.DataFrame:
    """Tabel rekomendasi.

    panel : PITPanel (data fundamental point-in-time EDGAR)
    closes: harga close per ticker (kolom = ticker)
    fund  : fundamental Yahoo (opsional, untuk kolom konteks)
    """
    asof = asof or closes.index[-1]
    snap = panel.snapshot(asof, closes.loc[:asof].iloc[-1])
    growth = edgar_scores(snap)["growth"]
    mom = momentum_score(closes, asof)

    idx = growth.dropna().index.union(mom.index)
    df = pd.DataFrame(index=idx)
    df["z_momentum"] = _z(mom.reindex(idx))
    df["z_growth"] = _z(growth.reindex(idx))

    # butuh minimal satu sinyal; bobot dinormalkan ke sinyal yang tersedia
    wm = df["z_momentum"].notna() * w_momentum
    wg = df["z_growth"].notna() * w_growth
    total_w = (wm + wg).replace(0, np.nan)
    df["skor"] = (df["z_momentum"].fillna(0) * wm +
                  df["z_growth"].fillna(0) * wg) / total_w
    df = df[df["skor"].notna()].copy()
    df["rekomendasi"] = df["skor"].apply(label_for)

    # kolom konteks fundamental (TIDAK memengaruhi skor)
    for col in ("net_margin", "roe", "rev_growth", "earnings_yield"):
        if col in snap.columns:
            df[col] = snap[col].reindex(df.index)
    if fund is not None:
        text_cols = ("shortName", "sector", "recommendationKey")
        num_cols = ("forwardPE", "marketCap", "currentPrice", "targetMeanPrice",
                    "targetHighPrice", "targetLowPrice",
                    "numberOfAnalystOpinions", "fiftyTwoWeekHigh",
                    "fiftyTwoWeekLow", "dividendYield")
        for col in text_cols:
            if col in fund.columns:
                df[col] = fund[col].reindex(df.index)
        for col in num_cols:
            if col in fund.columns:
                df[col] = pd.to_numeric(fund[col], errors="coerce").reindex(df.index)
        # potensi kenaikan ke target analis (%) — konteks, bukan penggerak
        cur = pd.to_numeric(df.get("currentPrice"), errors="coerce")
        tgt = pd.to_numeric(df.get("targetMeanPrice"), errors="coerce")
        df["upside_target"] = (tgt - cur) / cur
        # posisi harga dalam rentang 52 minggu (0 = low, 1 = high)
        hi = pd.to_numeric(df.get("fiftyTwoWeekHigh"), errors="coerce")
        lo = pd.to_numeric(df.get("fiftyTwoWeekLow"), errors="coerce")
        df["pos_52w"] = (cur - lo) / (hi - lo)
        # jarak dari puncak 52 mgg (negatif = di bawah puncak)
        df["dari_puncak"] = cur / hi - 1

    # return harga beberapa horizon (konteks)
    rets = compute_returns(closes.loc[:asof])
    for col in rets.columns:
        df[col] = rets[col].reindex(df.index)

    df = df.sort_values("skor", ascending=False)
    df.insert(0, "peringkat", range(1, len(df) + 1))
    return df
