"""M1 — Unduh companyfacts SEC EDGAR untuk seluruh universe saham.

Pakai: python scripts/fetch_edgar.py
"""
from _common import ROOT, load_config  # noqa: F401

from universe_sp500 import TICKERS

from src.stocks.edgar_client import EdgarClient

if __name__ == "__main__":
    client = EdgarClient(ROOT / "data" / "edgar_raw")
    cik_map = client.ticker_to_cik()

    ok, missing, failed = 0, [], []
    for i, t in enumerate(TICKERS, 1):
        key = t.upper().replace("-", "-")  # SEC pakai format BRK-B juga
        cik = cik_map.get(key)
        if cik is None:
            missing.append(t)
            continue
        data = client.companyfacts(t, cik)
        if data is None:
            failed.append(t)
            continue
        ok += 1
        if i % 20 == 0:
            print(f"{i}/{len(TICKERS)}...")

    print(f"\nSelesai: {ok} ticker tersimpan di data/edgar_raw/")
    if missing:
        print(f"CIK tidak ditemukan: {missing}")
    if failed:
        print(f"Gagal unduh: {failed}")
