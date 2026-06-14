# 📈 US Stock Monitor

Aplikasi web untuk memantau & menyaring saham US yang paling direkomendasikan.
Peringkat memakai dua sinyal: **momentum harga** (6 bulan) + **growth fundamental**
(pertumbuhan revenue & laba dari laporan resmi SEC EDGAR). Harga terkini, target
analis, dividen, dan berita ditampilkan sebagai konteks.

> ⚠️ Alat bantu riset — **bukan saran investasi**. Eksekusi pembelian dilakukan
> manual oleh pengguna di broker masing-masing.

## Coba langsung (deploy)

Aplikasi ini siap di-deploy gratis ke **Streamlit Community Cloud**:

1. Buka <https://share.streamlit.io> → login dengan GitHub.
2. **New app** → pilih repo ini → branch `main` → main file `app.py`.
3. Klik **Deploy**. Selesai — Anda dapat URL publik.

## Jalankan lokal

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# atau: .venv/bin/pip install -r requirements.txt  (Linux/Mac)
streamlit run app.py
```

Buka http://localhost:8501

## Cara skor dihitung

```
skor = z(momentum_6_bulan) + z(growth_revenue_dan_laba)
```

Keduanya sinyal yang melalui validasi backtest jujur (point-in-time, out-of-sample).
Valuasi, target analis, dan berita **tidak** memengaruhi peringkat — hanya konteks.

## Memperbarui data

Tombol "Refresh" di sidebar app, atau manual:

```bash
python scripts/fetch_stocks.py
python scripts/fetch_fundamentals.py
python scripts/fetch_edgar.py
python scripts/build_edgar_dataset.py
```

Data harga & fundamental dari Yahoo Finance; data fundamental point-in-time dari
SEC EDGAR (gratis, publik).

## Struktur

```
app.py                      # dashboard Streamlit
src/stocks/
├── signals.py              # skor rekomendasi (momentum + growth)
├── scoring.py              # z-score & skor faktor
├── pit_dataset.py          # panel fundamental point-in-time (EDGAR)
├── xbrl_normalize.py       # normalisasi XBRL → metrik standar
├── edgar_client.py         # client SEC EDGAR
├── fundamentals.py         # data fundamental Yahoo
└── news.py                 # headline berita
data/                       # harga, fundamental, panel EDGAR (ikut di repo)
scripts/                    # script pembaruan data
```
