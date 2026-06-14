"""M2 — Normalisasi XBRL companyfacts → tabel metrik standar.

Output per ticker: tabel long berisi
  (metric, start, end, val, filed, form, tag)
- Metrik flow (revenue, laba, arus kas) punya start+end (durasi).
- Metrik stock (aset, ekuitas, utang, kas, saham) hanya end.
- Dedup: filing PERTAMA per (metric, start, end) — sesuai PRD F2.3,
  angka yang diketahui investor saat itu, bukan hasil restatement.
- Tag dikumpulkan dari SEMUA kandidat per metrik (perusahaan sering ganti
  tag antar tahun); prioritas urutan list jadi tiebreak bila tanggal sama.
"""
import pandas as pd

# urutan = prioritas (PRD F2.1)
METRIC_TAGS = {
    "revenue": [
        # "Revenues" didahulukan: untuk asuransi/bank ini total sebenarnya,
        # untuk perusahaan biasa nilainya identik dengan tag contract ASC 606
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet", "RegulatedAndUnregulatedOperatingRevenue",
        # sektor finansial (bank/asuransi)
        "RevenuesNetOfInterestExpense", "InterestAndDividendIncomeOperating",
        "PremiumsEarnedNet",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss",
                   "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "op_income": ["OperatingIncomeLoss"],
    "assets": ["Assets"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "debt": ["LongTermDebt", "LongTermDebtNoncurrent",
             "DebtLongtermAndShorttermCombinedAmount"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
}
FLOW_METRICS = {"revenue", "net_income", "op_income", "cfo", "capex"}

SHARES_TAGS = [
    ("dei", "EntityCommonStockSharesOutstanding", "shares"),
    ("us-gaap", "CommonStockSharesOutstanding", "shares"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic", "shares"),
]


def _collect(taxonomy: dict, tag: str, unit: str, metric: str,
             priority: int) -> list[dict]:
    node = taxonomy.get(tag)
    if not node:
        return []
    recs = node.get("units", {}).get(unit, [])
    out = []
    for r in recs:
        if r.get("val") is None or not r.get("filed") or not r.get("end"):
            continue
        out.append({
            "metric": metric, "tag": tag, "prio": priority,
            "start": r.get("start"), "end": r["end"], "val": r["val"],
            "filed": r["filed"], "form": r.get("form", ""),
        })
    return out


def normalize_companyfacts(facts: dict) -> pd.DataFrame:
    gaap = facts.get("facts", {}).get("us-gaap", {})
    dei = facts.get("facts", {}).get("dei", {})

    rows: list[dict] = []
    for metric, tags in METRIC_TAGS.items():
        for prio, tag in enumerate(tags):
            rows.extend(_collect(gaap, tag, "USD", metric, prio))
    for prio, (tax, tag, unit) in enumerate(SHARES_TAGS):
        src = dei if tax == "dei" else gaap
        rows.extend(_collect(src, tag, unit, "shares", prio))

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["filed"] = pd.to_datetime(df["filed"])
    df["end"] = pd.to_datetime(df["end"])
    df["start"] = pd.to_datetime(df["start"])
    df["duration_d"] = (df["end"] - df["start"]).dt.days

    # filing pertama per (metric, start, end); prio tag sebagai tiebreak
    df = df.sort_values(["filed", "prio"])
    key = ["metric", "start", "end"]
    df = df.drop_duplicates(subset=key, keep="first")
    return df.drop(columns="prio").reset_index(drop=True)


def quarterly_flows(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Ambil nilai KUARTALAN murni untuk metrik flow (durasi ~1 kuartal).

    10-Q sering melaporkan YTD; baris berdurasi 70-110 hari adalah nilai
    kuartal tunggal. Q4 diturunkan dari (FY tahunan - 3 kuartal sebelumnya)
    di lapisan dataset (M3) bila kuartal langsungnya tidak tersedia.
    """
    d = df[(df["metric"] == metric) & df["duration_d"].between(70, 110)]
    return d.sort_values("end")


def annual_flows(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Nilai tahunan (durasi ~setahun, biasanya dari 10-K)."""
    d = df[(df["metric"] == metric) & df["duration_d"].between(340, 380)]
    return d.sort_values("end")


def point_values(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Metrik stock (balance sheet): nilai pada tanggal 'end'."""
    d = df[df["metric"] == metric]
    return d.sort_values("end")
