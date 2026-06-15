"""Digest rekomendasi otomatis (PRD v3.0 M2 / F1).

Menghitung rekomendasi terkini, menyusun ringkasan, lalu:
- menulis data/latest_digest.md (bisa dibaca di GitHub),
- menyimpan data/last_digest.json (state untuk hitung perubahan),
- mengirim ke Telegram BILA secret TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID ada.

Tanpa secret pun tetap jalan (hanya menulis file). Dipanggil oleh workflow
update-data setelah data di-refresh.

Pakai: python scripts/send_digest.py
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests

from _common import ROOT  # noqa: F401

from src.stocks.fundamentals import load_fundamentals
from src.stocks.pit_dataset import PITPanel
from src.stocks.signals import recommend

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BENCH = ["SPY", "QQQ"]
TOPN = 10
STATE = ROOT / "data" / "last_digest.json"
MD = ROOT / "data" / "latest_digest.md"            # premium (penuh)
MD_FREE = ROOT / "data" / "digest_free.md"          # teaser publik
# ganti dengan link checkout Anda (Substack/Gumroad/Stripe) saat sudah ada
SUBSCRIBE_URL = os.environ.get("SUBSCRIBE_URL", "https://your-substack-here")


def load_rec():
    fund = load_fundamentals(ROOT / "data" / "fundamentals.csv")
    closes = pd.read_parquet(ROOT / "data" / "prices.parquet")
    closes.index = pd.to_datetime(closes.index)
    panel = PITPanel(pd.read_parquet(ROOT / "data" / "edgar_normalized.parquet"))
    rec = recommend(panel, closes, fund)
    rec = rec.drop(index=[b for b in BENCH if b in rec.index], errors="ignore")
    rec = rec.sort_values("skor", ascending=False)
    return rec, closes.index[-1].date()


def earnings_days(r):
    ts = pd.to_numeric(r.get("earningsTimestampStart"), errors="coerce")
    if pd.isna(ts):
        ts = pd.to_numeric(r.get("earningsTimestamp"), errors="coerce")
    if pd.isna(ts):
        return None
    when = pd.to_datetime(ts, unit="s").normalize()
    return (when - pd.Timestamp.now().normalize()).days


def fmt_pct(v):
    return f"{v:+.0%}" if pd.notna(v) else "–"


def build(rec, data_date):
    top = rec.head(TOPN)
    prev = {}
    if STATE.exists():
        try:
            prev = json.loads(STATE.read_text())
        except Exception:
            prev = {}
    prev_top = set(prev.get("top", []))
    cur_top = list(top.index)
    new_in = [t for t in cur_top if t not in prev_top]
    dropped = [t for t in prev_top if t not in cur_top]

    n_strong = int((rec["skor"] >= 1.0).sum())
    n_buy = int(((rec["skor"] >= 0.3) & (rec["skor"] < 1.0)).sum())
    soon = []
    for t, r in rec.head(40).iterrows():
        d = earnings_days(r)
        if d is not None and 0 <= d <= 7:
            soon.append(f"{t} ({d}d)")

    # ---------- PREMIUM (penuh, untuk pelanggan) ----------
    p = [f"📈 *US Stock Monitor — Premium Digest · {data_date}*", "",
         f"_{n_strong} strongly recommended · {n_buy} recommended · "
         f"{len(rec)} S&P 500 stocks · momentum + growth model_", "",
         f"*Top {TOPN}:*"]
    for rank, (t, r) in enumerate(top.iterrows(), 1):
        price = pd.to_numeric(r.get("currentPrice"), errors="coerce")
        up = pd.to_numeric(r.get("upside_target"), errors="coerce")
        ret = pd.to_numeric(r.get("ret_1Th"), errors="coerce")
        ptxt = f"${price:,.0f}" if pd.notna(price) else "–"
        p.append(f"{rank}. *{t}* — score {r['skor']:+.2f} · {ptxt} · "
                 f"analyst target {fmt_pct(up)} · 1y {fmt_pct(ret)}")
    if new_in:
        p += ["", f"🆕 *New in top {TOPN}:* " + ", ".join(new_in)]
    if dropped:
        p += [f"🔻 *Dropped from top {TOPN}:* " + ", ".join(dropped)]
    if soon:
        p += ["", "📅 *Earnings within 7 days:* " + ", ".join(soon)]
    p += ["", "_Research tool, not investment advice. You execute trades "
          "yourself._"]
    premium = "\n".join(p)

    # ---------- FREE (teaser publik, untuk menarik pelanggan) ----------
    f = [f"📈 *US Stock Monitor — Free Weekly Digest · {data_date}*", "",
         f"This week: *{n_strong} strongly recommended* and {n_buy} recommended "
         f"out of {len(rec)} S&P 500 stocks (momentum + growth model).", "",
         "*Today's top 3:* " + ", ".join(cur_top[:3]) + " …"]
    if new_in:
        f += [f"🆕 {len(new_in)} new name(s) entered the top {TOPN} this week."]
    if soon:
        f += [f"📅 {len(soon)} top pick(s) report earnings within 7 days."]
    f += ["",
          f"🔓 *Premium* unlocks the full top {TOPN} with scores, prices, "
          "analyst targets, every ranking change, earnings alerts & watchlist "
          "signals — delivered weekly.",
          f"👉 Subscribe: {SUBSCRIBE_URL}", "",
          "_Research tool, not investment advice._"]
    free = "\n".join(f)

    STATE.write_text(json.dumps({"date": str(data_date), "top": cur_top}),
                     encoding="utf-8")
    MD.write_text(premium.replace("*", "**"), encoding="utf-8")
    MD_FREE.write_text(free.replace("*", "**"), encoding="utf-8")
    return premium


def send_telegram(text):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("Telegram secret tidak ada — lewati kirim (file digest tetap dibuat).")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "Markdown",
                  "disable_web_page_preview": True}, timeout=30)
        print("Telegram:", "terkirim" if r.ok else f"gagal {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"Telegram error: {e}")


if __name__ == "__main__":
    rec, data_date = load_rec()
    msg = build(rec, data_date)
    print(msg)
    print("-" * 40)
    send_telegram(msg)
    print(f"Digest ditulis: {MD}")
