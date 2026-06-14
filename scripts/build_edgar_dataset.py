"""M2 — Normalisasi semua companyfacts + laporan kualitas.

Output: data/edgar_normalized.parquet (tabel long semua ticker).
Uji kualitas (PRD F2.4, versi M2): cakupan per ticker + sanity margin laba
tahunan terakhir vs profitMargins Yahoo. Perbandingan ketat berbasis TTM
dilakukan di M3 (saat TTM tersedia).

Pakai: python scripts/build_edgar_dataset.py
"""
import json
from pathlib import Path

import pandas as pd

from _common import ROOT, load_config  # noqa: F401

from src.stocks.fundamentals import load_fundamentals
from src.stocks.xbrl_normalize import annual_flows, normalize_companyfacts

RAW = ROOT / "data" / "edgar_raw"
OUT = ROOT / "data" / "edgar_normalized.parquet"

if __name__ == "__main__":
    frames, coverage = [], []
    for f in sorted(RAW.glob("*.json")):
        if f.name == "company_tickers.json":
            continue
        t = f.stem
        df = normalize_companyfacts(json.loads(f.read_text()))
        if df.empty:
            coverage.append({"ticker": t, "q_revenue": 0, "tahun": 0})
            continue
        df["ticker"] = t
        frames.append(df)
        rev = df[(df["metric"] == "revenue") & df["duration_d"].between(70, 110)]
        years = (df["end"].max() - df["end"].min()).days / 365.25
        coverage.append({"ticker": t, "q_revenue": len(rev),
                         "tahun": round(years, 1),
                         "filing_terakhir": df["filed"].max().date()})

    alldf = pd.concat(frames, ignore_index=True)
    alldf.to_parquet(OUT, index=False)
    cov = pd.DataFrame(coverage).set_index("ticker")
    print(f"Tersimpan: {OUT} ({len(alldf):,} baris, "
          f"{alldf['ticker'].nunique()} ticker)\n")

    # --- cakupan (target PRD G1: >=90% ticker punya >=40 kuartal revenue) ---
    ok = (cov["q_revenue"] >= 40).mean()
    print(f"Cakupan: {ok:.0%} ticker punya >=40 kuartal revenue "
          f"(target >=90%)")
    weak = cov[cov["q_revenue"] < 40].sort_values("q_revenue")
    if len(weak):
        print(f"Ticker di bawah 40 kuartal:\n{weak.to_string()}\n")

    # --- sanity: margin laba tahunan terakhir vs Yahoo ---
    fund = load_fundamentals(ROOT / "data" / "fundamentals.csv")
    devs = []
    for t, g in alldf.groupby("ticker"):
        rev = annual_flows(g, "revenue")
        ni = annual_flows(g, "net_income")
        if rev.empty or ni.empty or fund is None or t not in fund.index:
            continue
        last_end = min(rev["end"].max(), ni["end"].max())
        r = rev[rev["end"] == last_end]["val"]
        n = ni[ni["end"] == last_end]["val"]
        ym = pd.to_numeric(fund.loc[t, "profitMargins"], errors="coerce")
        if r.empty or n.empty or pd.isna(ym) or r.iloc[0] == 0:
            continue
        em = n.iloc[0] / r.iloc[0]
        devs.append({"ticker": t, "margin_edgar_FY": round(em, 3),
                     "margin_yahoo_TTM": round(ym, 3),
                     "selisih": round(abs(em - ym), 3)})
    dv = pd.DataFrame(devs).set_index("ticker").sort_values("selisih",
                                                            ascending=False)
    big = (dv["selisih"] > 0.10).mean()
    print(f"Sanity margin laba (FY EDGAR vs TTM Yahoo, beda periode wajar): "
          f"{big:.0%} ticker selisih >10 poin")
    print("\n15 selisih terbesar (periksa manual bila mencurigakan):")
    print(dv.head(15).to_string())
    cov.to_csv(ROOT / "data" / "edgar_coverage.csv")
