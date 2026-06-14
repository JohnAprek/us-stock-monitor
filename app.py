"""US Stock Monitor — pantau & saring saham US yang paling direkomendasikan.

Peringkat memakai 2 sinyal tervalidasi: momentum harga (6 bulan) + growth
fundamental (pertumbuhan revenue & laba dari laporan SEC). Valuasi, target
analis, return, dividen, dan berita ditampilkan sebagai konteks — tidak
memengaruhi peringkat.

Jalankan: streamlit run app.py
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

st.set_page_config(page_title="US Stock Monitor", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

# ---------- gaya / CSS ----------
st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {
    background: #f8f9fb; border: 1px solid #eaecf0; border-radius: 12px;
    padding: 14px 16px;
}
[data-testid="stMetricLabel"] {opacity: .7;}
.badge {display:inline-block; padding:3px 10px; border-radius:999px;
    font-size:.78rem; font-weight:600; white-space:nowrap;}
.b-strong{background:#dcfce7;color:#15803d;}
.b-buy{background:#e0f2fe;color:#0369a1;}
.b-neutral{background:#f1f5f9;color:#475569;}
.b-weak{background:#fef3c7;color:#b45309;}
.pick-card{background:#fff;border:1px solid #eaecf0;border-radius:14px;
    padding:14px 16px;height:100%;}
.pick-tkr{font-size:1.15rem;font-weight:700;margin-bottom:2px;}
.pick-name{font-size:.78rem;color:#64748b;margin-bottom:8px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.muted{color:#64748b;font-size:.82rem;}
.posbar{height:8px;border-radius:6px;background:#e2e8f0;position:relative;}
.posbar > div{position:absolute;top:-3px;width:14px;height:14px;border-radius:50%;
    background:#0ea5e9;transform:translateX(-50%);}
</style>
""", unsafe_allow_html=True)


def badge_class(label: str) -> str:
    if "Sangat" in label:
        return "b-strong"
    if "✅" in label:
        return "b-buy"
    if "➖" in label:
        return "b-neutral"
    return "b-weak"


def badge_html(label: str) -> str:
    return f'<span class="badge {badge_class(label)}">{label}</span>'


# ---------- data ----------
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
    return recommend(panel, closes, fund, w_momentum=w_mom, w_growth=w_grw), closes, fund


fund0, closes0 = load_prices_fund()
if fund0 is None or load_panel() is None:
    st.error("Data belum lengkap. Jalankan dulu:\n\n"
             "`python scripts/fetch_stocks.py`\n"
             "`python scripts/fetch_fundamentals.py`\n"
             "`python scripts/fetch_edgar.py`\n"
             "`python scripts/build_edgar_dataset.py`")
    st.stop()

# ---------- sidebar ----------
st.sidebar.title("📈 US Stock Monitor")
st.sidebar.caption("Pantau & saring saham US paling direkomendasikan.")

with st.sidebar.expander("🔄 Perbarui data", expanded=False):
    def run_refresh(scripts):
        logs = []
        for label, script in scripts:
            with st.spinner(f"{label}..."):
                p = subprocess.run([sys.executable, f"scripts/{script}"],
                                   cwd=str(ROOT), capture_output=True, text=True)
            logs.append(f"{'✅' if p.returncode == 0 else '❌'} {label}")
        st.cache_data.clear()
        st.session_state["refresh_log"] = logs

    if st.button("Harga + Fundamental", use_container_width=True):
        run_refresh([("Harga", "fetch_stocks.py"),
                     ("Fundamental", "fetch_fundamentals.py")])
        st.rerun()
    if st.button("+ Laporan SEC (kuartalan)", use_container_width=True):
        run_refresh([("Harga", "fetch_stocks.py"),
                     ("Fundamental", "fetch_fundamentals.py"),
                     ("SEC unduh", "fetch_edgar.py"),
                     ("SEC olah", "build_edgar_dataset.py")])
        st.rerun()
    for line in st.session_state.get("refresh_log", []):
        st.caption(line)

st.sidebar.subheader("⚙️ Bobot sinyal")
w_mom = st.sidebar.slider("Momentum harga", 0.0, 2.0, 1.0, 0.25)
w_grw = st.sidebar.slider("Growth fundamental", 0.0, 2.0, 1.0, 0.25)
st.sidebar.caption("Default 1:1 — dua sinyal tervalidasi proyek ini.")

rec, closes, fund = get_recommendations(w_mom, w_grw)
data_date = closes.index[-1].date()

st.sidebar.subheader("🔎 Filter")
sectors = ["Semua"] + sorted(rec["sector"].dropna().unique())
sel_sector = st.sidebar.selectbox("Sektor", sectors)
only_rec = st.sidebar.checkbox("Hanya yang direkomendasikan (skor ≥ 0,3)", True)
min_upside = st.sidebar.slider("Upside ke target analis min. (%)", -20, 50, -20, 5)
div_only = st.sidebar.checkbox("Hanya yang membayar dividen", False)
sort_by = st.sidebar.selectbox(
    "Urutkan",
    ["Skor", "Upside analis", "Momentum", "Growth", "Return 1 tahun",
     "Dividend yield", "Kapitalisasi"])
search = st.sidebar.text_input("Cari ticker / nama").strip().upper()

SORT_MAP = {"Skor": "skor", "Upside analis": "upside_target",
            "Momentum": "z_momentum", "Growth": "z_growth",
            "Return 1 tahun": "ret_1Th", "Dividend yield": "dividendYield",
            "Kapitalisasi": "marketCap"}

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
    m = view.index.str.contains(search) | \
        view["shortName"].fillna("").str.upper().str.contains(search)
    view = view[m]
view = view.sort_values(SORT_MAP[sort_by], ascending=False)

# ---------- header + ringkasan ----------
st.title("📈 US Stock Monitor")
st.caption(f"Saham US paling direkomendasikan · momentum + pertumbuhan "
           f"fundamental · data per **{data_date}** · {len(rec)} saham dianalisis. "
           f"Alat bantu riset, bukan saran investasi.")

n_strong = int((rec["skor"] >= 1.0).sum())
n_buy = int(((rec["skor"] >= 0.3) & (rec["skor"] < 1.0)).sum())
avg_up = rec["upside_target"].median()
best_ret = rec["ret_1Th"].median() if "ret_1Th" in rec else float("nan")
m = st.columns(4)
m[0].metric("⭐ Sangat direkomendasikan", n_strong)
m[1].metric("✅ Direkomendasikan", n_buy)
m[2].metric("Median upside analis",
            f"{avg_up:+.0%}" if pd.notna(avg_up) else "–")
m[3].metric("Median return 1 thn",
            f"{best_ret:+.0%}" if pd.notna(best_ret) else "–")

tab1, tab2, tab3 = st.tabs(["⭐ Rekomendasi", "📊 Ringkasan Pasar",
                            "🔍 Detail Saham"])

# ============ TAB 1: REKOMENDASI ============
with tab1:
    st.markdown("##### 🏆 5 Teratas")
    top5 = rec.head(5)
    cards = st.columns(5)
    for col, (tkr, r) in zip(cards, top5.iterrows()):
        up = r["upside_target"]
        up_txt = f"{up:+.0%}" if pd.notna(up) else "–"
        price = r.get("currentPrice")
        price_txt = f"${price:,.2f}" if pd.notna(price) else "–"
        col.markdown(f"""
<div class="pick-card">
  <div class="pick-tkr">{tkr}</div>
  <div class="pick-name">{str(r.get('shortName', ''))[:22]}</div>
  {badge_html(r['rekomendasi'])}
  <div style="margin-top:10px;" class="muted">Harga {price_txt}</div>
  <div class="muted">Target analis {up_txt}</div>
  <div class="muted">Skor {r['skor']:+.2f}</div>
</div>""", unsafe_allow_html=True)

    st.markdown(f"##### 📋 Daftar ({len(view)} saham · urut: {sort_by})")
    cols_show = ["peringkat", "shortName", "sector", "rekomendasi", "skor",
                 "z_momentum", "z_growth", "currentPrice", "targetMeanPrice",
                 "upside_target", "ret_3B", "ret_1Th", "dari_puncak",
                 "dividendYield", "forwardPE", "recommendationKey"]
    show = view[[c for c in cols_show if c in view.columns]].copy()
    show.columns = ["#", "Nama", "Sektor", "Rekomendasi", "Skor", "Mom",
                    "Growth", "Harga", "Target", "Upside", "Ret 3B", "Ret 1Th",
                    "Dari puncak", "Div", "P/E", "Analis"]
    st.dataframe(
        show.style
        .background_gradient(subset=["Skor"], cmap="RdYlGn", vmin=-2, vmax=2)
        .format({"Skor": "{:+.2f}", "Mom": "{:+.2f}", "Growth": "{:+.2f}",
                 "Harga": "${:.2f}", "Target": "${:.2f}", "Upside": "{:+.1%}",
                 "Ret 3B": "{:+.1%}", "Ret 1Th": "{:+.1%}",
                 "Dari puncak": "{:+.1%}", "Div": "{:.2f}%", "P/E": "{:.1f}"},
                na_rep="–"),
        width="stretch", height=520, hide_index=True)
    st.caption("**Penggerak skor:** Momentum & Growth. **Konteks (tak "
               "memengaruhi peringkat):** harga, target & rekomendasi analis, "
               "return, jarak dari puncak, dividen, P/E. Target analis cenderung "
               "optimistis — perlakukan sebagai info.")

# ============ TAB 2: RINGKASAN PASAR ============
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Distribusi rekomendasi")
        dist = rec["rekomendasi"].value_counts()
        st.bar_chart(dist, horizontal=True, color="#0ea5e9")
    with c2:
        st.markdown("##### Skor rata-rata per sektor")
        by_sec = (rec.groupby("sector")["skor"].mean()
                  .sort_values(ascending=False))
        st.bar_chart(by_sec, horizontal=True, color="#15803d")

    st.markdown("##### Peta sinyal: Momentum vs Growth")
    st.caption("Kanan-atas = momentum & growth sama-sama kuat (paling menarik). "
               "Ukuran ≈ skor.")
    scat = rec[["z_momentum", "z_growth", "rekomendasi", "sector"]].copy()
    scat = scat.dropna()
    st.scatter_chart(scat, x="z_momentum", y="z_growth", color="rekomendasi",
                     height=420)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("##### 🚀 Return tertinggi (1 tahun)")
        topret = (rec.dropna(subset=["ret_1Th"])
                  .nlargest(8, "ret_1Th")[["shortName", "ret_1Th", "rekomendasi"]])
        topret.columns = ["Nama", "Return 1Th", "Rekomendasi"]
        st.dataframe(topret.style.format({"Return 1Th": "{:+.1%}"}),
                     width="stretch", hide_index=True)
    with c4:
        st.markdown("##### 💰 Dividen tertinggi")
        topdiv = (rec.dropna(subset=["dividendYield"])
                  .nlargest(8, "dividendYield")
                  [["shortName", "dividendYield", "rekomendasi"]])
        topdiv.columns = ["Nama", "Div yield", "Rekomendasi"]
        st.dataframe(topdiv.style.format({"Div yield": "{:.2f}%"}),
                     width="stretch", hide_index=True)

# ============ TAB 3: DETAIL SAHAM ============
with tab3:
    pick = st.selectbox("Pilih saham",
                        view.index.tolist() or rec.index.tolist())
    if pick:
        r = rec.loc[pick]

        def num(k):
            return pd.to_numeric(r.get(k), errors="coerce")

        st.markdown(f"### {r.get('shortName', pick)} ({pick}) "
                    f"&nbsp; {badge_html(r['rekomendasi'])}",
                    unsafe_allow_html=True)
        st.caption(f"{r.get('sector', '')} · peringkat #{int(r['peringkat'])} "
                   f"dari {len(rec)}")

        k = st.columns(4)
        k[0].metric("Skor total", f"{r['skor']:+.2f}")
        k[1].metric("Momentum", f"{r['z_momentum']:+.2f}")
        k[2].metric("Growth", f"{r['z_growth']:+.2f}")
        cur, tgt = num("currentPrice"), num("targetMeanPrice")
        k[3].metric("Harga", f"${cur:,.2f}" if pd.notna(cur) else "–",
                    f"{(tgt-cur)/cur:+.1%} ke target" if pd.notna(tgt) and pd.notna(cur) else None)

        left, right = st.columns([3, 2])
        with left:
            st.markdown("**Harga 2 tahun**")
            if pick in closes.columns:
                st.line_chart(closes[pick].dropna().tail(504), height=260)
            # posisi dalam rentang 52 minggu
            pos = num("pos_52w")
            lo52, hi52 = num("fiftyTwoWeekLow"), num("fiftyTwoWeekHigh")
            if pd.notna(pos):
                pos = max(0.0, min(1.0, pos))
                st.markdown(f"""<div class="muted">Posisi 52 minggu</div>
<div class="posbar"><div style="left:{pos*100:.0f}%"></div></div>
<div style="display:flex;justify-content:space-between" class="muted">
<span>${lo52:,.0f}</span><span>${hi52:,.0f}</span></div>""",
                            unsafe_allow_html=True)

        with right:
            st.markdown("**Return**")
            rc = st.columns(4)
            for col, (lbl, key) in zip(rc, [("1B", "ret_1B"), ("3B", "ret_3B"),
                                            ("6B", "ret_6B"), ("1Th", "ret_1Th")]):
                v = num(key)
                col.metric(lbl, f"{v:+.0%}" if pd.notna(v) else "–")

            st.markdown("**Analis**")
            rk = str(r.get("recommendationKey", "–")).upper().replace("_", " ")
            no = num("numberOfAnalystOpinions")
            tl, th = num("targetLowPrice"), num("targetHighPrice")
            st.write({
                "Konsensus": rk,
                "Jumlah analis": int(no) if pd.notna(no) else "–",
                "Target rata-rata": f"${tgt:,.2f}" if pd.notna(tgt) else "–",
                "Rentang target": f"${tl:,.0f} – ${th:,.0f}" if pd.notna(tl) else "–",
            })

        st.markdown("**📊 Fundamental** _(konteks — tidak memengaruhi skor)_")
        fcols = st.columns(4)
        items = [
            ("Net margin", "net_margin", "{:.1%}"),
            ("Operating margin", "op_margin", "{:.1%}"),
            ("ROE", "roe", "{:.1%}"),
            ("Rev growth (YoY)", "rev_growth", "{:.1%}"),
            ("Earnings yield", "earnings_yield", "{:.1%}"),
            ("Fwd P/E", "forwardPE", "{:.1f}"),
            ("Dividend yield", "dividendYield", "{:.2f}%"),
            ("Kapitalisasi", "marketCap", "${:,.0f}"),
        ]
        for i, (lbl, key, fmt) in enumerate(items):
            v = num(key)
            fcols[i % 4].metric(lbl, fmt.format(v) if pd.notna(v) else "–")

        st.markdown("**📰 Berita terbaru** _(informasi — belum jadi sinyal)_")
        news = get_news(pick)
        if not news:
            st.caption("Tidak ada berita yang diambil.")
        for n in news:
            title = f"[{n['title']}]({n['url']})" if n["url"] else n["title"]
            st.markdown(
                f"- {title}  \n  <small class='muted'>{n['publisher']} · "
                f"{n['date']}</small>", unsafe_allow_html=True)
