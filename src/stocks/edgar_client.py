"""Client SEC EDGAR (data.sec.gov) — gratis, tanpa API key.

Aturan SEC: sertakan User-Agent berisi kontak, dan <= 10 request/detik.
Kita pakai throttle konservatif ~7 req/detik + retry eksponensial.
Semua respons di-cache ke data/edgar_raw/ supaya unduhan bisa diulang
tanpa membebani SEC.
"""
import json
import time
from pathlib import Path

import requests

USER_AGENT = "kizamu-research yohanesafry34@gmail.com"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
MIN_INTERVAL = 0.15  # detik antar request (~7/s)


class EdgarClient:
    def __init__(self, cache_dir: Path):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last_req = 0.0

    def _get(self, url: str) -> dict:
        for attempt in range(5):
            wait = self._last_req + MIN_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_req = time.monotonic()
            r = self.session.get(url, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
        raise RuntimeError(f"Gagal setelah 5 percobaan: {url}")

    def ticker_to_cik(self) -> dict[str, int]:
        """Peta ticker -> CIK (di-cache sehari-harian tidak perlu, sekali cukup)."""
        p = self.cache / "company_tickers.json"
        if p.exists():
            raw = json.loads(p.read_text())
        else:
            raw = self._get(TICKERS_URL)
            p.write_text(json.dumps(raw))
        return {v["ticker"].upper(): int(v["cik_str"]) for v in raw.values()}

    def companyfacts(self, ticker: str, cik: int, force: bool = False) -> dict | None:
        """Seluruh fakta XBRL perusahaan. Cache per ticker."""
        p = self.cache / f"{ticker}.json"
        if p.exists() and not force:
            return json.loads(p.read_text())
        try:
            data = self._get(FACTS_URL.format(cik=cik))
        except Exception as e:
            print(f"{ticker}: gagal ({e})")
            return None
        p.write_text(json.dumps(data))
        return data

    def latest_filing_date(self, cik: int) -> str | None:
        """Tanggal filing terbaru (untuk refresh inkremental)."""
        try:
            sub = self._get(SUBMISSIONS_URL.format(cik=cik))
            dates = sub["filings"]["recent"]["filingDate"]
            return max(dates) if dates else None
        except Exception:
            return None
