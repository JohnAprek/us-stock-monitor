"""US Stock Monitor — pantau & saring saham US yang paling direkomendasikan.

Rekomendasi memakai 2 sinyal: momentum harga (6 bulan) + growth fundamental
(pertumbuhan revenue & laba dari laporan resmi SEC). Fundamental lain & berita
ditampilkan sebagai konteks — tidak memengaruhi peringkat.

Jalankan: .venv\\Scripts\\streamlit run app.py
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from src.stocks.fundamentals import load_fundamentals
from src.stocks.news import get_news
from src.stocks.pit_dataset import PITPanel
from src.stocks.signals import recommend

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="US Stock Monitor", layout="wide")
st.title("📈 US Stock Monitor")
st.caption("Saham US paling direkomendasikan — momentum harga + pertumbuhan "
           "fundamental. Alat bantu riset, bukan saran investasi.")


@st.cache_data(ttl=3600)
def load_prices_fund():
    fund = load_fundamentals(ROOT / "data" / "fundamentals.csv")
    cols = {}
    for f in sorted((ROOT / "data" / "stocks").glob("*.csv")):
        d = pd.read_csv(f, index_col=0, parse_dates=True)
        cols[f.stem] = d["close"]
    return fund, pd.DataFrame(cols)


@st.cache_resource
def load_panel():
    pq = ROOT / "data" / "edgar_normalized.parquet"
    return PITPanel(pd.read_parquet(pq)) if pq.exists() else None


@st.cache_data(ttl=1800)
def get_recommendations(w_mom, w_grw):
    fund, closes = load_prices_fund()
    panel = load_panel()
    if panel is None or fund is None:
        return None, closes, fund
    rec = recommend(panel, closes, fund, w_momentum=w_mom, w_growth=w_grw)
    return rec, closes, fund


fund, closes = load_prices_fund()
if fund is None or load_panel() is None:
    st.error("Data belum lengkap. Jalankan dulu:\n\n"
             "`python scripts/fetch_stocks.py`\n"
             "`python scripts/fetch_fundamentals.py`\n"
             "`python scripts/fetch_edgar.py`\n"
             "`python scripts/build_edgar_dataset.py`")
    st.stop()

# ---- sidebar: refresh, bobot, filter ----
st.sidebar.header("🔄 Data")


def run_refresh(scripts):
    logs = []
    for label, script in scripts:
        with st.spinner(f"{label}..."):
            p = subprocess.run([sys.executable, f"scripts/{script}"],
                               cwd=str(ROOT), capture_output=True, text=True)
        logs.append(f"{'✅' if p.returncode == 0 else '❌'} {label}")
    st.cache_data.clear()
    st.session_state["refresh_log"] = logs


col_a, col_b = st.sidebar.columns(2)
if col_a.button("Harga + Fundamental", use_container_width=True):
    run_refresh([("Harga", "fetch_stocks.py"),
                 ("Fundamental", "fetch_fundamentals.py")])
    st.rerun()
if col_b.button("+ Laporan SEC", use_container_width=True):
    run_refresh([("Harga", "fetch_stocks.py"),
                 ("Fundamental", "fetch_fundamentals.py"),
                 ("SEC unduh", "fetch_edgar.py"),
                 ("SEC olah", "build_edgar_dataset.py")])
    st.rerun()
for line in st.session_state.get("refresh_log", []):
    st.sidebar.caption(line)

st.sidebar.header("⚙️ Pengaturan sinyal")
w_mom = st.sidebar.slider("Bobot Momentum", 0.0, 2.0, 1.0, 0.25)
w_grw = st.sidebar.slider("Bobot Growth", 0.0, 2.0, 1.0, 0.25)
st.sidebar.caption("Default 1:1 — keduanya sinyal yang dipakai proyek ini.")

rec, closes, fund = get_recommendations(w_mom, w_grw)
data_date = closes.index[-1].date()

st.sidebar.header("🔎 Filter")
sectors = ["Semua"] + sorted(rec["sector"].dropna().unique())
sel_sector = st.sidebar.selectbox("Sektor", sectors)
only_rec = st.sidebar.checkbox("Hanya yang direkomendasikan", value=True)
min_upside = st.sidebar.slider("Upside ke target analis minimal (%)",
                               -20, 50, -20, 5)
div_only = st.sidebar.checkbox("Hanya yang membayar dividen", value=False)
search = st.sidebar.text_input("Cari ticker / nama").strip().upper()

view = rec.copy()
if sel_sector != "Semua":
    view = view[view["sector"] == sel_sector]
if only_rec:
    view = view[view["skor"] >= 0.3]
if min_upside > -20:
    view = view[view["upside_target"] >= min_upside / 100]
if div_only:
    view = view[view["dividendYield"].fillna(0) > 0]
if search:
    mask = view.index.str.contains(search) | \
        view["shortName"].fillna("").str.upper().str.contains(search)
    view = view[mask]

tab1, tab2 = st.tabs(["⭐ Rekomendasi", "🔍 Detail saham"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Saham dianalisis", len(rec))
    c2.metric("Direkomendasikan (skor ≥ 0,3)", int((rec["skor"] >= 0.3).sum()))
    c3.metric("Data harga per", str(data_date))

    show = view[["peringkat", "shortName", "sector", "rekomendasi", "skor",
                 "z_momentum", "z_growth", "currentPrice", "targetMeanPrice",
                 "upside_target", "dari_puncak", "dividendYield",
                 "recommendationKey", "forwardPE"]].copy()
    show.columns = ["#", "Nama", "Sektor", "Rekomendasi", "Skor", "Momentum",
                    "Growth", "Harga", "Target", "Upside", "Dari puncak",
                    "Div yield", "Analis", "Fwd P/E"]
    st.dataframe(
        show.style
        .background_gradient(subset=["Skor"], cmap="RdYlGn")
        .format({"Skor": "{:+.2f}", "Momentum": "{:+.2f}", "Growth": "{:+.2f}",
                 "Harga": "${:.2f}", "Target": "${:.2f}", "Upside": "{:+.1%}",
                 "Dari puncak": "{:+.1%}", "Div yield": "{:.2f}%",
                 "Fwd P/E": "{:.1f}"}, na_rep="–"),
        width="stretch", height=560)
    st.caption("**Penggerak skor:** Momentum & Growth saja. "
               "**Konteks (tidak memengaruhi peringkat):** Harga, Target analis, "
               "Upside, rekomendasi Analis, P/E. Target analis cenderung "
               "optimistis — perlakukan sebagai info, bukan janji.")

with tab2:
    pick = st.selectbox("Pilih saham", view.index.tolist() or rec.index.tolist())
    if pick:
        r = rec.loc[pick]
        st.subheader(f"{r.get('shortName', pick)} ({pick}) — {r['rekomendasi']}")
        cc = st.columns(4)
        cc[0].metric("Peringkat", f"#{int(r['peringkat'])} / {len(rec)}")
        cc[1].metric("Skor total", f"{r['skor']:+.2f}")
        cc[2].metric("Momentum", f"{r['z_momentum']:+.2f}")
        cc[3].metric("Growth", f"{r['z_growth']:+.2f}")

        def num(key):
            return pd.to_numeric(r.get(key), errors="coerce")

        cur, tgt = num("currentPrice"), num("targetMeanPrice")
        st.markdown("**💲 Harga & target analis** _(konteks — bukan penggerak skor)_")
        pc = st.columns(4)
        pc[0].metric("Harga saat ini", f"${cur:.2f}" if pd.notna(cur) else "–")
        if pd.notna(tgt) and pd.notna(cur):
            pc[1].metric("Target rata-rata", f"${tgt:.2f}",
                         f"{(tgt - cur) / cur:+.1%} upside")
        else:
            pc[1].metric("Target rata-rata", "–")
        lo52, hi52 = num("fiftyTwoWeekLow"), num("fiftyTwoWeekHigh")
        dari_puncak = num("dari_puncak")
        pc[2].metric("Rentang 52 mgg",
                     f"${lo52:.0f} – ${hi52:.0f}" if pd.notna(lo52) else "–",
                     f"{dari_puncak:+.1%} dari puncak" if pd.notna(dari_puncak) else None)
        rk = str(r.get("recommendationKey", "–")).upper()
        no = num("numberOfAnalystOpinions")
        pc[3].metric("Konsensus analis", rk,
                     f"{int(no)} analis" if pd.notna(no) else None)
        tl, th = num("targetLowPrice"), num("targetHighPrice")
        dy = num("dividendYield")
        if pd.notna(tl) and pd.notna(th):
            st.caption(f"Rentang target analis: ${tl:.2f} (terendah) – "
                       f"${th:.2f} (tertinggi). Target analis historisnya bias "
                       "optimistis — bukan jaminan.")
        if pd.notna(dy) and dy > 0:
            st.caption(f"Dividend yield: {dy:.2f}% per tahun.")

        left, right = st.columns([2, 1])
        with left:
            if pick in closes.columns:
                st.line_chart(closes[pick].dropna().tail(504))  # ~2 tahun
        with right:
            st.markdown("**Konteks fundamental** _(tak memengaruhi skor)_")
            st.write({
                "Sektor": r.get("sector"),
                "Fwd P/E": round(r["forwardPE"], 1) if pd.notna(r.get("forwardPE")) else "–",
                "Net margin": f"{r['net_margin']:.1%}" if pd.notna(r.get("net_margin")) else "–",
                "ROE": f"{r['roe']:.1%}" if pd.notna(r.get("roe")) else "–",
                "Rev growth": f"{r['rev_growth']:.1%}" if pd.notna(r.get("rev_growth")) else "–",
                "Earnings yield": f"{r['earnings_yield']:.1%}" if pd.notna(r.get("earnings_yield")) else "–",
            })

        st.markdown("**📰 Berita terbaru** _(informasi — belum jadi sinyal)_")
        news = get_news(pick)
        if not news:
            st.caption("Tidak ada berita yang diambil.")
        for n in news:
            title = f"[{n['title']}]({n['url']})" if n["url"] else n["title"]
            st.markdown(f"- {title}  \n  <small>{n['publisher']} · {n['date']}</small>",
                        unsafe_allow_html=True)
