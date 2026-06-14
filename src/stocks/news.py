"""Ambil headline berita per saham via yfinance (gratis).

Hanya menampilkan informasi — tidak ada skor sentimen, tidak memengaruhi
rekomendasi. Untuk membantu pengguna cek konteks sebelum membeli.
"""
import yfinance as yf


def get_news(ticker: str, limit: int = 6) -> list[dict]:
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    out = []
    for it in items[:limit]:
        c = it.get("content", it)  # format yfinance bisa nested di 'content'
        title = c.get("title") or it.get("title")
        if not title:
            continue
        pub = c.get("pubDate") or c.get("providerPublishTime") or ""
        url = ""
        if isinstance(c.get("clickThroughUrl"), dict):
            url = c["clickThroughUrl"].get("url", "")
        url = url or it.get("link", "")
        provider = ""
        if isinstance(c.get("provider"), dict):
            provider = c["provider"].get("displayName", "")
        out.append({"title": title, "publisher": provider or it.get("publisher", ""),
                    "date": str(pub)[:10], "url": url})
    return out
