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
/* kartu adaptif tema (terang/gelap) via variabel Streamlit */
[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,.2); border-radius: 12px;
    padding: 14px 16px;
}
[data-testid="stMetricLabel"] {opacity: .7;}
.badge {display:inline-block; padding:3px 10px; border-radius:999px;
    font-size:.78rem; font-weight:600; white-space:nowrap;}
.b-strong{background:#dcfce7;color:#15803d;}
.b-buy{background:#e0f2fe;color:#0369a1;}
.b-neutral{background:#e2e8f0;color:#475569;}
.b-weak{background:#fef3c7;color:#b45309;}
.pick-card{background:var(--secondary-background-color);
    border:1px solid rgba(128,128,128,.2);border-radius:14px;
    padding:14px 16px;height:100%;}
.pick-tkr{font-size:1.15rem;font-weight:700;margin-bottom:2px;}
.pick-name{font-size:.78rem;opacity:.65;margin-bottom:8px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.muted{opacity:.65;font-size:.82rem;}
.posbar{height:8px;border-radius:6px;background:rgba(128,128,128,.25);
    position:relative;}
.posbar > div{position:absolute;top:-3px;width:14px;height:14px;border-radius:50%;
    background:var(--primary-color, #0ea5e9);transform:translateX(-50%);}
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


BENCHMARKS = ["SPY", "QQQ"]


def subscribe_url():
    """URL langganan premium (Substack). Diisi di data/subscribe_url.txt."""
    f = ROOT / "data" / "subscribe_url.txt"
    try:
        u = f.read_text(encoding="utf-8").strip()
        return u if u and "your-substack-here" not in u else None
    except Exception:
        return None


def earnings_days(r):
    """Sisa hari ke rilis laba berikutnya (dari earningsTimestampStart)."""
    ts = pd.to_numeric(r.get("earningsTimestampStart"), errors="coerce")
    if pd.isna(ts):
        ts = pd.to_numeric(r.get("earningsTimestamp"), errors="coerce")
    if pd.isna(ts):
        return None
    when = pd.to_datetime(ts, unit="s").normalize()
    return (when - pd.Timestamp.now().normalize()).days


# ---------- data ----------
@st.cache_data(ttl=3600)
def load_prices_fund():
    fund = load_fundamentals(ROOT / "data" / "fundamentals.csv")
    pq = ROOT / "data" / "prices.parquet"
    if pq.exists():                      # konsolidasi cepat (S&P 500)
        closes = pd.read_parquet(pq)
        closes.index = pd.to_datetime(closes.index)
        return fund, closes.sort_index()
    cols = {}                            # fallback: CSV per ticker
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
    if closes is None or closes.empty:
        return None, closes, fund, {"prices": False, "growth": False, "fund": False}
    try:
        rec = recommend(panel, closes, fund, w_momentum=w_mom, w_growth=w_grw)
        rec = rec.drop(index=[b for b in BENCHMARKS if b in rec.index],
                       errors="ignore")
        # peringkat ulang setelah benchmark dibuang
        rec = rec.sort_values("skor", ascending=False)
        rec["peringkat"] = range(1, len(rec) + 1)
    except Exception as e:  # degradasi anggun: jangan pernah blank
        rec = None
        st.session_state["rec_error"] = str(e)
    status = {"prices": True, "growth": panel is not None,
              "fund": fund is not None}
    return rec, closes, fund, status


fund0, closes0 = load_prices_fund()
if closes0 is None or closes0.empty:
    st.error("Data harga belum ada. Jalankan dulu:\n\n"
             "`python scripts/fetch_stocks.py`")
    st.stop()

# ---------- sidebar ----------
st.sidebar.title("📈 US Stock Monitor")
st.sidebar.caption("Pantau & saring saham US paling direkomendasikan.")

_sub = subscribe_url()
if _sub:
    st.sidebar.link_button("⭐ Get Premium Digest", _sub,
                           use_container_width=True, type="primary")
    st.sidebar.caption("Weekly top picks + ranking changes + earnings alerts.")

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
        run_refresh([("Harga", "fetch_prices.py"),
                     ("Fundamental", "fetch_fundamentals.py")])
        st.rerun()
    if st.button("+ Laporan SEC (kuartalan)", use_container_width=True):
        run_refresh([("Harga", "fetch_prices.py"),
                     ("Fundamental", "fetch_fundamentals.py"),
                     ("SEC unduh", "fetch_edgar.py"),
                     ("SEC olah", "build_edgar_dataset.py")])
        st.rerun()
    for line in st.session_state.get("refresh_log", []):
        st.caption(line)

with st.sidebar.expander("ℹ️ Status data", expanded=False):
    import datetime as _dt

    def _age(path):
        p = ROOT / "data" / path
        if not p.exists():
            return "—"
        days = (_dt.datetime.now().timestamp() - p.stat().st_mtime) / 86400
        return f"{days:.0f} hari lalu"

    st.caption(f"Harga: {_age('prices.parquet')}")
    st.caption(f"Fundamental: {_age('fundamentals.csv')}")
    st.caption(f"Laporan SEC: {_age('edgar_normalized.parquet')}")

st.sidebar.subheader("⚙️ Bobot sinyal")
w_mom = st.sidebar.slider("Momentum harga", 0.0, 2.0, 1.0, 0.25)
w_grw = st.sidebar.slider("Growth fundamental", 0.0, 2.0, 1.0, 0.25)
st.sidebar.caption("Default 1:1 — dua sinyal tervalidasi proyek ini.")

rec, closes, fund, status = get_recommendations(w_mom, w_grw)
data_date = closes.index[-1].date()

if rec is None or rec.empty:
    st.error("Gagal menyusun rekomendasi dari data yang ada. "
             "Coba perbarui data lewat sidebar.")
    if st.session_state.get("rec_error"):
        st.caption(f"Detail: {st.session_state['rec_error']}")
    st.stop()

# pastikan semua kolom opsional ada (NaN bila sumbernya bolong) → UI tak crash
OPTIONAL_COLS = ["shortName", "sector", "currentPrice", "targetMeanPrice",
                 "targetLowPrice", "targetHighPrice", "upside_target",
                 "recommendationKey", "numberOfAnalystOpinions",
                 "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "pos_52w", "dari_puncak",
                 "dividendYield", "forwardPE", "marketCap", "net_margin",
                 "op_margin", "gross_margin", "fcf_margin", "current_ratio",
                 "buyback_yoy", "roe", "rev_growth", "earnings_yield",
                 "ret_1B", "ret_3B", "ret_6B", "ret_1Th"]
for c in OPTIONAL_COLS:
    if c not in rec.columns:
        rec[c] = pd.NA

# hari ke rilis laba berikutnya (konteks)
rec["laba_hari"] = rec.apply(earnings_days, axis=1)

# banner degradasi: bila salah satu sumber data bolong, app tetap jalan
if not status["growth"]:
    st.warning("⚠️ Data fundamental SEC (growth) tidak tersedia — peringkat "
               "memakai **momentum saja**. Perbarui via sidebar untuk skor penuh.")
if not status["fund"]:
    st.info("ℹ️ Data harga/target analis (Yahoo) tidak tersedia — kolom konteks "
            "mungkin kosong. Peringkat tetap dari momentum + growth.")

# ---------- watchlist (tersimpan di URL, bisa di-bookmark) ----------
def get_watchlist():
    raw = st.query_params.get("wl", "")
    return [t for t in raw.split(",") if t]


def set_watchlist(tickers):
    st.query_params["wl"] = ",".join(sorted(set(tickers)))


st.sidebar.subheader("⭐ Watchlist")
wl_now = [t for t in get_watchlist() if t in rec.index]
wl = st.sidebar.multiselect("Saham favorit (tersimpan di URL)",
                            options=rec.index.tolist(), default=wl_now)
if set(wl) != set(wl_now):
    set_watchlist(wl)
    st.rerun()
only_wl = st.sidebar.checkbox(f"Hanya watchlist ({len(wl)})", False,
                              disabled=not wl)

st.sidebar.subheader("🔎 Filter")
compact = st.sidebar.toggle("📱 Tampilan ringkas (HP)", False)
preset = st.sidebar.selectbox(
    "Preset screener",
    ["Custom", "Growth + dividen", "Momentum kuat & dekat puncak",
     "Skor tinggi & upside analis ≥ 15%"])
sectors = ["Semua"] + sorted(rec["sector"].dropna().unique())
sel_sector = st.sidebar.selectbox("Sektor", sectors)
search = st.sidebar.text_input("Cari ticker / nama").strip().upper()

manual = preset == "Custom"
only_rec = st.sidebar.checkbox("Hanya direkomendasikan (skor ≥ 0,3)", True,
                               disabled=not manual)
min_upside = st.sidebar.slider("Upside ke target analis min. (%)", -20, 50, -20,
                               5, disabled=not manual)
div_only = st.sidebar.checkbox("Hanya yang membayar dividen", False,
                               disabled=not manual)
sort_by = st.sidebar.selectbox(
    "Urutkan",
    ["Skor", "Upside analis", "Momentum", "Growth", "Return 1 tahun",
     "Dividend yield", "Kapitalisasi"])

SORT_MAP = {"Skor": "skor", "Upside analis": "upside_target",
            "Momentum": "z_momentum", "Growth": "z_growth",
            "Return 1 tahun": "ret_1Th", "Dividend yield": "dividendYield",
            "Kapitalisasi": "marketCap"}


def num_col(df, c):
    return pd.to_numeric(df[c], errors="coerce")


view = rec.copy()
if only_wl and wl:
    view = view[view.index.isin(wl)]
if sel_sector != "Semua":
    view = view[view["sector"] == sel_sector]
if search:
    m = view.index.str.contains(search) | \
        view["shortName"].fillna("").str.upper().str.contains(search)
    view = view[m]

if preset == "Growth + dividen":
    view = view[(view["skor"] >= 0.3) & (view["z_growth"] >= 0.3) &
                (num_col(view, "dividendYield").fillna(0) > 0)]
elif preset == "Momentum kuat & dekat puncak":
    view = view[(view["z_momentum"] >= 0.5) &
                (num_col(view, "dari_puncak") >= -0.10)]
elif preset == "Skor tinggi & upside analis ≥ 15%":
    view = view[(view["skor"] >= 0.5) &
                (num_col(view, "upside_target") >= 0.15)]
else:  # Custom
    if only_rec:
        view = view[view["skor"] >= 0.3]
    if min_upside > -20:
        view = view[num_col(view, "upside_target") >= min_upside / 100]
    if div_only:
        view = view[num_col(view, "dividendYield").fillna(0) > 0]

view = view.sort_values(SORT_MAP[sort_by], ascending=False)

# ---------- header + ringkasan ----------
st.title("📈 US Stock Monitor")
st.caption(f"Saham US paling direkomendasikan · momentum + pertumbuhan "
           f"fundamental · data per **{data_date}** · {len(rec)} saham dianalisis. "
           f"Alat bantu riset, bukan saran investasi.")

with st.expander("ℹ️ Apa arti skor & rekomendasi ini? (baca dulu)"):
    st.markdown("""
**Peringkat ditentukan oleh 2 hal saja** (yang terbukti punya nilai lewat
backtest jujur di proyek ini):

- **Momentum** — saham yang harganya menguat 6 bulan terakhir cenderung
  melanjutkan tren dalam jangka menengah.
- **Growth** — perusahaan yang revenue & labanya tumbuh (dari laporan resmi SEC).

Skor adalah gabungan keduanya, **relatif terhadap ~113 saham lain** (z-score).
Skor `+1` berarti jauh di atas rata-rata; `0` rata-rata; negatif di bawah.

**Yang HANYA konteks (tidak memengaruhi peringkat):** harga, target & rekomendasi
analis, valuasi (P/E), dividen, return, berita. Berguna untuk menilai, tapi
bukan dasar peringkat — mis. target analis terkenal terlalu optimistis.

**Batasan jujur:** universe ini saham yang bertahan sampai sekarang
(*survivorship bias* → angka cenderung terlalu bagus), dan periode uji tak
memuat krisis 2008. Ini **alat penyaring**, bukan jaminan profit. Tetap baca
bisnisnya, dan **eksekusi beli dilakukan manual** oleh Anda di broker sendiri.
""")

n_strong = int((rec["skor"] >= 1.0).sum())
n_buy = int(((rec["skor"] >= 0.3) & (rec["skor"] < 1.0)).sum())
avg_up = pd.to_numeric(rec["upside_target"], errors="coerce").median()
best_ret = pd.to_numeric(rec["ret_1Th"], errors="coerce").median()


def bench_ret(tkr, days=252):
    if tkr in closes.columns and len(closes) > days:
        s = closes[tkr].dropna()
        if len(s) > days:
            return s.iloc[-1] / s.iloc[-1 - days] - 1
    return float("nan")


spy_ret = bench_ret("SPY")
m = st.columns(5)
m[0].metric("⭐ Sangat direkomendasikan", n_strong)
m[1].metric("✅ Direkomendasikan", n_buy)
m[2].metric("Median upside analis",
            f"{avg_up:+.0%}" if pd.notna(avg_up) else "–")
m[3].metric("Median return 1 thn",
            f"{best_ret:+.0%}" if pd.notna(best_ret) else "–")
m[4].metric("SPY (S&P 500) 1 thn",
            f"{spy_ret:+.0%}" if pd.notna(spy_ret) else "–",
            help="Acuan pasar — bandingkan return median saham vs beli indeks.")

tab1, tab5, tab2, tab4, tab3 = st.tabs(
    ["⭐ Rekomendasi", "📬 Digest", "📊 Ringkasan Pasar",
     "⚖️ Banding", "🔍 Detail Saham"])

# ============ TAB 1: REKOMENDASI ============
with tab1:
    st.markdown("##### 🏆 5 Teratas")
    top5 = rec.head(5)
    cards = st.columns(5)
    for col, (tkr, r) in zip(cards, top5.iterrows()):
        up = pd.to_numeric(r.get("upside_target"), errors="coerce")
        up_txt = f"{up:+.0%}" if pd.notna(up) else "–"
        price = pd.to_numeric(r.get("currentPrice"), errors="coerce")
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

    head_l, head_r = st.columns([3, 1])
    head_l.markdown(f"##### 📋 Daftar ({len(view)} saham · urut: {sort_by}"
                    + (f" · preset: {preset}" if preset != "Custom" else "") + ")")
    head_r.download_button("⬇️ Unduh CSV", view.to_csv().encode("utf-8"),
                           "rekomendasi.csv", "text/csv",
                           use_container_width=True)

    if compact:
        cols_show = ["peringkat", "shortName", "rekomendasi", "skor",
                     "currentPrice", "upside_target"]
        names = ["#", "Nama", "Rekomendasi", "Skor", "Harga", "Upside"]
        fmt = {"Skor": "{:+.2f}", "Harga": "${:.2f}", "Upside": "{:+.1%}"}
    else:
        cols_show = ["peringkat", "shortName", "sector", "rekomendasi", "skor",
                     "z_momentum", "z_growth", "currentPrice", "targetMeanPrice",
                     "upside_target", "ret_3B", "ret_1Th", "dari_puncak",
                     "dividendYield", "forwardPE", "laba_hari", "recommendationKey"]
        names = ["#", "Nama", "Sektor", "Rekomendasi", "Skor", "Mom", "Growth",
                 "Harga", "Target", "Upside", "Ret 3B", "Ret 1Th", "Dari puncak",
                 "Div", "P/E", "Laba (hari)", "Analis"]
        fmt = {"Skor": "{:+.2f}", "Mom": "{:+.2f}", "Growth": "{:+.2f}",
               "Harga": "${:.2f}", "Target": "${:.2f}", "Upside": "{:+.1%}",
               "Ret 3B": "{:+.1%}", "Ret 1Th": "{:+.1%}", "Dari puncak": "{:+.1%}",
               "Div": "{:.2f}%", "P/E": "{:.1f}", "Laba (hari)": "{:.0f}"}
    show = view[[c for c in cols_show if c in view.columns]].copy()
    show.columns = names
    st.dataframe(
        show.style
        .background_gradient(subset=["Skor"], cmap="RdYlGn", vmin=-2, vmax=2)
        .format(fmt, na_rep="–"),
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

# ============ TAB 4: BANDING ============
with tab4:
    st.markdown("##### ⚖️ Banding 2–4 saham")
    default_cmp = (wl[:3] if wl else rec.index[:3].tolist())
    picks = st.multiselect("Pilih saham (maks 4)", rec.index.tolist(),
                           default=default_cmp, max_selections=4)
    show_spy = st.checkbox("Tampilkan SPY (acuan pasar)", True)
    if len(picks) >= 2:
        rows = []
        for t in picks:
            rr = rec.loc[t]
            def g(k):
                return pd.to_numeric(rr.get(k), errors="coerce")
            rows.append({
                "Ticker": t, "Nama": rr.get("shortName"),
                "Rekomendasi": rr["rekomendasi"], "Skor": rr["skor"],
                "Momentum": rr["z_momentum"], "Growth": rr["z_growth"],
                "Harga": g("currentPrice"), "Upside": g("upside_target"),
                "Ret 1Th": g("ret_1Th"), "Net margin": g("net_margin"),
                "ROE": g("roe"), "Rev growth": g("rev_growth"),
                "P/E": g("forwardPE"), "Div": g("dividendYield"),
            })
        cmp = pd.DataFrame(rows).set_index("Ticker")
        st.dataframe(
            cmp.style.format({
                "Skor": "{:+.2f}", "Momentum": "{:+.2f}", "Growth": "{:+.2f}",
                "Harga": "${:.2f}", "Upside": "{:+.1%}", "Ret 1Th": "{:+.1%}",
                "Net margin": "{:.1%}", "ROE": "{:.1%}", "Rev growth": "{:.1%}",
                "P/E": "{:.1f}", "Div": "{:.2f}%"}, na_rep="–"),
            width="stretch")

        st.markdown("**Perbandingan harga (ternormalisasi ke 100, 1 tahun)**")
        series = picks + (["SPY"] if show_spy and "SPY" in closes.columns else [])
        norm = closes[series].dropna(how="all").tail(252)
        norm = norm / norm.iloc[0] * 100
        st.line_chart(norm, height=320)
        st.caption("Garis di atas 100 = naik sejak setahun lalu. Bandingkan "
                   "lintasan tiap saham terhadap SPY (pasar).")
    else:
        st.info("Pilih minimal 2 saham untuk membandingkan.")

# ============ TAB 5: DIGEST ============
with tab5:
    st.markdown(f"##### 📬 Digest rekomendasi · data {data_date}")
    st.caption("Ringkasan yang juga dikirim otomatis ke Telegram tiap minggu "
               "(jika diaktifkan). Perubahan dihitung sejak digest terakhir.")

    import json as _json
    state_p = ROOT / "data" / "last_digest.json"
    prev_top = set()
    if state_p.exists():
        try:
            prev_top = set(_json.loads(state_p.read_text(encoding="utf-8"))
                           .get("top", []))
        except Exception:
            prev_top = set()

    top10 = rec.head(10)
    cur_top = list(top10.index)
    new_in = [t for t in cur_top if t not in prev_top]
    dropped = [t for t in prev_top if t not in cur_top]

    if new_in or dropped:
        cda, cdb = st.columns(2)
        cda.success("🆕 Masuk top 10: " + (", ".join(new_in) if new_in else "–"))
        cdb.warning("🔻 Keluar top 10: " + (", ".join(dropped) if dropped else "–"))

    dg = top10[["shortName", "rekomendasi", "skor", "currentPrice",
                "upside_target", "ret_1Th"]].copy()
    dg.insert(0, "#", range(1, len(dg) + 1))
    dg.columns = ["#", "Nama", "Rekomendasi", "Skor", "Harga", "Upside", "Ret 1Th"]
    st.dataframe(
        dg.style.format({"Skor": "{:+.2f}", "Harga": "${:.2f}",
                         "Upside": "{:+.1%}", "Ret 1Th": "{:+.1%}"}, na_rep="–"),
        width="stretch", hide_index=True)

    soon = []
    for t, rr in rec.head(40).iterrows():
        d = earnings_days(rr)
        if d is not None and 0 <= d <= 7:
            soon.append(f"{t} ({d}h)")
    if soon:
        st.info("📅 Rilis laba ≤ 7 hari: " + ", ".join(soon))

    _sub2 = subscribe_url()
    if _sub2:
        st.success("📬 **Get this digest every week** — full top 10, ranking "
                   "changes & earnings alerts delivered to your inbox.")
        st.link_button("⭐ Subscribe to Premium", _sub2, type="primary")

    with st.expander("🔔 Aktifkan kiriman Telegram (sekali setup)"):
        st.markdown("""
1. Telegram → chat **@BotFather** → `/newbot` → salin **token**.
2. Chat **@userinfobot** → salin **Id** (angka) Anda.
3. Tekan **Start** di bot baru Anda.
4. GitHub repo → **Settings → Secrets and variables → Actions** → tambah
   `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID`.
5. Uji: **Actions → Update data → Run workflow**. Digest masuk ke Telegram.
""")

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

        ed = earnings_days(r)
        if ed is not None and 0 <= ed <= 7:
            st.warning(f"📅 **Rilis laba dalam {ed} hari** — harga bisa "
                       "bergejolak. Pertimbangkan menunggu.")
        elif ed is not None and ed > 7:
            st.caption(f"📅 Rilis laba berikutnya ~{ed} hari lagi.")

        in_wl = pick in wl
        if st.button(("✅ Di watchlist — klik untuk hapus" if in_wl
                      else "⭐ Tambah ke watchlist"), key="wl_btn"):
            new_wl = [t for t in wl if t != pick] if in_wl else wl + [pick]
            set_watchlist(new_wl)
            st.rerun()

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
            ("Gross margin", "gross_margin", "{:.1%}"),
            ("Operating margin", "op_margin", "{:.1%}"),
            ("Net margin", "net_margin", "{:.1%}"),
            ("FCF margin", "fcf_margin", "{:.1%}"),
            ("ROE", "roe", "{:.1%}"),
            ("Rev growth (YoY)", "rev_growth", "{:.1%}"),
            ("Current ratio", "current_ratio", "{:.2f}"),
            ("Buyback (YoY)", "buyback_yoy", "{:+.1%}"),
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
