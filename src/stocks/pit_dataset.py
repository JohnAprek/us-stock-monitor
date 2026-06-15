"""M3 — Panel fundamental point-in-time.

Aturan emas (PRD F3.2): sebuah angka baru boleh dipakai mulai 1 hari bursa
SETELAH tanggal filing-nya. Semua fungsi di sini menerima `asof` dan hanya
membaca baris dengan filed <= asof.

Logika kuartal:
- Baris berdurasi ~90 hari = nilai kuartal langsung.
- Pelapor YTD: kuartal yang hilang diturunkan dari selisih (YTD - jumlah
  kuartal yang sudah diketahui di dalamnya), termasuk Q4 = FY - 9M.
  Kuartal turunan mewarisi tanggal filing TERBESAR dari komponennya.
- TTM = jumlah 4 kuartal terakhir yang ter-filing, dengan syarat rentang
  total 330-400 hari (mencegah jumlah kuartal bolong).
"""
import numpy as np
import pandas as pd

from src.stocks.xbrl_normalize import FLOW_METRICS


def quarter_series(rows: pd.DataFrame) -> pd.DataFrame:
    """rows: baris satu metrik flow satu ticker → kuartal (start,end,val,filed)."""
    rows = rows.dropna(subset=["start"]).sort_values("end")
    quarters: dict = {}

    for r in rows[rows["duration_d"].between(70, 110)].itertuples():
        q = quarters.get(r.end)
        if q is None or r.filed < q["filed"]:
            quarters[r.end] = {"start": r.start, "end": r.end,
                               "val": r.val, "filed": r.filed}

    # turunkan kuartal hilang dari YTD/annual, urut durasi naik (H1→9M→FY)
    ytd = rows[rows["duration_d"] > 110].sort_values(["end", "duration_d"])
    for r in ytd.itertuples():
        if r.end in quarters:
            continue
        inside = sorted(
            (q for q in quarters.values()
             if q["start"] >= r.start - pd.Timedelta(days=10)
             and q["end"] < r.end),
            key=lambda q: q["end"])
        if not inside or abs((inside[0]["start"] - r.start).days) > 10:
            continue
        chain = [inside[0]]
        for q in inside[1:]:
            if 0 <= (q["start"] - chain[-1]["end"]).days <= 10:
                chain.append(q)
        gap = (r.end - chain[-1]["end"]).days
        if 70 <= gap <= 110:
            quarters[r.end] = {
                "start": chain[-1]["end"], "end": r.end,
                "val": r.val - sum(q["val"] for q in chain),
                "filed": max([r.filed] + [q["filed"] for q in chain]),
            }

    if not quarters:
        return pd.DataFrame(columns=["start", "end", "val", "filed"])
    return pd.DataFrame(quarters.values()).sort_values("end").reset_index(drop=True)


def ttm(quarters: pd.DataFrame, asof: pd.Timestamp, back: int = 0) -> float:
    """TTM pada `asof` (hanya kuartal ter-filing). back=4 → TTM setahun lalu."""
    k = quarters[quarters["filed"] <= asof].sort_values("end")
    if back:
        k = k.iloc[:-back] if len(k) > back else k.iloc[0:0]
    last4 = k.tail(4)
    if len(last4) < 4:
        return np.nan
    span = (last4["end"].iloc[-1] - last4["start"].iloc[0]).days
    if not 330 <= span <= 400:
        return np.nan
    return float(last4["val"].sum())


def latest_point(rows: pd.DataFrame, asof: pd.Timestamp) -> float:
    """Nilai balance-sheet terbaru yang sudah ter-filing pada `asof`."""
    k = rows[rows["filed"] <= asof].sort_values("end")
    return float(k["val"].iloc[-1]) if len(k) else np.nan


def point_back(rows: pd.DataFrame, asof: pd.Timestamp, back_days: int = 365) -> float:
    """Nilai point ~back_days sebelum titik terbaru (untuk hitung perubahan YoY)."""
    k = rows[rows["filed"] <= asof].sort_values("end")
    if k.empty:
        return np.nan
    target = k["end"].iloc[-1] - pd.Timedelta(days=back_days)
    prior = k[k["end"] <= target]
    return float(prior["val"].iloc[-1]) if len(prior) else np.nan


class PITPanel:
    def __init__(self, normalized: pd.DataFrame):
        self.q: dict = {}       # (ticker, metric) -> kuartal
        self.pt: dict = {}      # (ticker, metric) -> point rows
        for (t, m), g in normalized.groupby(["ticker", "metric"]):
            if m in FLOW_METRICS:
                self.q[(t, m)] = quarter_series(g)
            else:
                self.pt[(t, m)] = g.sort_values("end")
        self.tickers = sorted({t for t, _ in
                               list(self.q.keys()) + list(self.pt.keys())})

    def snapshot(self, asof: pd.Timestamp,
                 prices: pd.Series | None = None,
                 split_factor: pd.Series | None = None) -> pd.DataFrame:
        """Rasio fundamental per ticker, hanya dari data ter-filing <= asof.

        prices: harga close SPLIT-ADJUSTED pada tanggal keputusan (PRD F3.3).
        split_factor: faktor split kumulatif SETELAH asof per ticker —
            saham EDGAR (basis saat itu) dikali faktor ini supaya sebasis
            dengan harga split-adjusted. mcap = harga x saham x faktor
            = market cap historis yang benar.
        """
        rows = {}
        for t in self.tickers:
            def T(m, back=0):
                qd = self.q.get((t, m))
                return ttm(qd, asof, back) if qd is not None else np.nan

            def P(m):
                pr = self.pt.get((t, m))
                return latest_point(pr, asof) if pr is not None else np.nan

            def PB(m, days=365):
                pr = self.pt.get((t, m))
                return point_back(pr, asof, days) if pr is not None else np.nan

            rev, rev_prior = T("revenue"), T("revenue", back=4)
            ni, ni_prior = T("net_income"), T("net_income", back=4)
            op = T("op_income")
            fcf = T("cfo") - T("capex") if not np.isnan(T("cfo")) else np.nan
            eq, debt, shares = P("equity"), P("debt"), P("shares")
            gp, cogs = T("gross_profit"), T("cogs")
            cur_a, cur_l = P("cur_assets"), P("cur_liab")
            shares_prior = PB("shares")

            mcap = np.nan
            if prices is not None and t in prices.index and shares and shares > 0:
                factor = 1.0
                if split_factor is not None and t in split_factor.index:
                    factor = split_factor[t]
                mcap = prices[t] * shares * factor

            rows[t] = {
                "roe": ni / eq if eq and eq > 0 else np.nan,
                "net_margin": ni / rev if rev else np.nan,
                "op_margin": op / rev if rev else np.nan,
                "debt_equity": debt / eq if eq and eq > 0 else np.nan,
                "rev_growth": rev / rev_prior - 1 if rev_prior else np.nan,
                "ni_growth": ni / ni_prior - 1
                             if ni_prior and ni_prior > 0 else np.nan,
                "earnings_yield": ni / mcap if mcap and mcap > 0 else np.nan,
                "book_price": eq / mcap if mcap and mcap > 0 else np.nan,
                "fcf_yield": fcf / mcap if mcap and mcap > 0 else np.nan,
                # M7 (B4): metrik lebih dalam
                "gross_margin": (gp / rev if not np.isnan(gp) and rev
                                 else ((rev - cogs) / rev
                                       if not np.isnan(cogs) and rev else np.nan)),
                "fcf_margin": fcf / rev if not np.isnan(fcf) and rev else np.nan,
                "current_ratio": cur_a / cur_l if cur_l and cur_l > 0 else np.nan,
                "buyback_yoy": (-(shares / shares_prior - 1)
                                if shares_prior and shares_prior > 0 else np.nan),
                "ttm_revenue": rev, "ttm_ni": ni, "mcap": mcap,
            }
        return pd.DataFrame(rows).T
