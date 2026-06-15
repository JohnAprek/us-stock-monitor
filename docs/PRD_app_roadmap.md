# PRD — US Stock Monitor v2.0 (UI/UX, Data, Keandalan)

**Versi:** 2.0 · **Tanggal:** 2026-06-14 · **Status:** Draft untuk persetujuan
**Repo:** github.com/JohnAprek/us-stock-monitor (deploy: Streamlit Community Cloud)
**Melanjutkan:** PRD_stock_app v1.1 (aplikasi inti — sudah live)

---

## 1. Ringkasan & posisi sekarang

Aplikasi sudah **live di web** (Streamlit Cloud): meranking 113 saham US dengan
momentum + growth, menampilkan harga, target analis, return, dividen, fundamental,
berita, plus tab Ringkasan Pasar. PRD ini menaikkan kualitas dari "berfungsi"
menjadi "enak dipakai harian & datanya selalu segar", tanpa mengubah inti
metodologi (momentum + growth tetap satu-satunya penggerak peringkat).

Tiga arah perbaikan:
- **UI/UX** — nyaman di HP, watchlist, banding saham, onboarding, ekspor.
- **Data** — auto-update mingguan, universe lebih luas, data lebih dalam &
  konteks pasar, jaga batas memori Streamlit Cloud gratis.
- **Keandalan** — pin versi, penanganan error, persistensi pengaturan.

## 2. Masalah / peluang

1. **Data bisa basi.** Streamlit Cloud gratis bersifat ephemeral — refresh manual
   di app tidak permanen; data hanya seglobal commit terakhir. Butuh auto-update.
2. **Akses HP belum optimal.** Tabel lebar meluber di layar kecil; pengguna utama
   mengakses dari ponsel.
3. **Tidak ada personalisasi.** Tak bisa menandai saham favorit, membandingkan,
   atau menyimpan filter — padahal alur "pantau rutin" butuh ini.
4. **Universe sempit (113).** Banyak saham menarik di luar daftar.
5. **Risiko kerapuhan deploy.** Versi dependency tidak dipin → update Streamlit
   bisa mematahkan `scatter_chart`/`horizontal=True`, dll.
6. **Konteks pasar minim.** Tidak ada pembanding indeks (SPY) atau kalender laba.

## 3. Tujuan & metrik sukses

| # | Tujuan | Metrik |
|---|--------|--------|
| G1 | Data selalu segar otomatis | GitHub Action mingguan commit data baru; badge "data per <tanggal>" ≤ 7 hari |
| G2 | Nyaman di HP | Tabel utama terbaca tanpa scroll horizontal berlebihan di lebar 390px |
| G3 | Personalisasi dasar | Watchlist & filter tersimpan antar sesi (per browser) |
| G4 | Universe lebih luas | ≥ 300 saham tanpa melebihi batas memori Streamlit Cloud (~1 GB) |
| G5 | Deploy tahan banting | Versi dependency dipin; app tak pernah blank karena 1 data bolong |
| G6 | Konteks lebih kaya | Pembanding indeks + kalender laba + banding antar-saham |

**Definisi sukses:** pengguna membuka app dari HP beberapa kali seminggu, melihat
data segar, menandai & membandingkan saham incaran, tanpa app pernah error.

## 4. Non-goals (di luar scope v2)

- ❌ Eksekusi order / koneksi broker (selamanya manual — desain inti)
- ❌ Menambah penggerak peringkat baru tanpa backtest (value/quality/berita tetap
  konteks; pagar metodologi v1.1 berlaku)
- ❌ Akun pengguna / login / multi-user dengan database server
- ❌ Data intraday / real-time tick (tetap harian)
- ❌ Saham non-US / non-SEC
- ❌ Notifikasi push / email (kandidat v3)

## 5. Epic UI/UX

### A1 — Responsif & mobile-first
- Deteksi layar sempit → tabel utama tampilkan subset kolom prioritas
  (Nama, Rekomendasi, Skor, Harga, Upside); sisanya di Detail.
- Kartu "5 Teratas" menumpuk vertikal di HP (bukan 5 kolom).
- Sidebar default collapsed di mobile.

### A2 — Watchlist (favorit)
- Tombol ⭐ per saham → simpan ke watchlist.
- Tab/filter "Hanya watchlist".
- Persistensi: `st.query_params` + (opsional) ekspor/impor daftar watchlist
  sebagai teks, karena Streamlit Cloud tak punya storage permanen per-user.

### A3 — Banding saham (compare)
- Pilih 2–4 saham → tabel berdampingan: skor, momentum, growth, valuasi,
  return, target, dividen; overlay grafik harga ternormalisasi.

### A4 — Onboarding & edukasi
- Panel "Apa arti skor ini?" yang bisa dilipat: jelaskan momentum & growth
  dalam bahasa awam + pengingat keterbatasan (survivorship, bukan saran).
- Tooltip per kolom tabel.

### A5 — Preset screener & ekspor
- Preset 1-klik: "Growth + dividen", "Momentum kuat & belum jauh dari puncak",
  "Direkomendasikan & upside analis tinggi".
- Tombol unduh hasil tampilan ke CSV.

### A6 — Tema & polish
- Toggle terang/gelap.
- Format mata uang: tampilkan USD + estimasi IDR (kurs dari data, diberi label
  "perkiraan").

## 6. Epic Data

### B1 — Auto-update via GitHub Actions (PRIORITAS)
- Workflow cron mingguan (mis. Senin pagi): jalankan `fetch_stocks` +
  `fetch_fundamentals` (+ `fetch_edgar`/`build` bulanan) → commit data → push.
- Streamlit Cloud auto-redeploy pada commit → app selalu segar tanpa campur
  tangan manual.
- Aman: tanpa secret (Yahoo & SEC publik); hormati rate-limit SEC.

### B2 — Perluas universe (113 → 300–500)
- Tambah ticker secara objektif (kapitalisasi & likuiditas, bukan performa —
  anti-snooping). Target S&P 500 atau subset besar.
- Pemeliharaan: tanggal masuk per ticker; buang delisting/merger.

### B3 — Efisiensi memori (mengikat B2)
- Konsolidasi harga ke 1 file Parquet (bukan 300+ CSV) → muat sekali, hemat.
- Pertimbangkan menyimpan hanya ~3 tahun harga untuk app (cukup untuk
  momentum & grafik); arsip penuh tetap di repo riset terpisah.
- Target: footprint < 700 MB RAM saat 500 saham.

### B4 — Data lebih dalam (EDGAR)
- Tambah metrik: arus kas bebas detail, buyback (shares turun), gross margin,
  current ratio. Pakai panel point-in-time yang sudah ada.

### B5 — Konteks pasar
- Pembanding indeks: SPY/US500 (harga & return) sebagai baris acuan.
- Kalender laba: tanggal rilis laporan berikutnya per saham (dari Yahoo),
  tandai saham yang akan rilis ≤ 7 hari ("hati-hati, laba segera").

### B6 — Mutu & kesegaran data
- Indikator umur data per sumber (harga, fundamental, EDGAR) di header.
- Cek sanity saat build (mis. harga nol/negatif, ticker hilang) → log peringatan.

## 7. Epic Keandalan & Deploy

### C1 — Pin versi dependency
- `requirements.txt` dengan versi tetap (streamlit, pandas, numpy, pyarrow,
  yfinance) yang sudah teruji → cegah update memecah UI.

### C2 — Degradasi anggun
- Bila satu sumber data bolong (mis. EDGAR gagal) → app tetap jalan dengan
  momentum-only + banner "growth tidak tersedia", bukan blank/crash.
- Bungkus tiap pemanggilan eksternal (berita, dll) dengan try/except + pesan.

### C3 — Persistensi pengaturan
- Filter & watchlist via `st.query_params` (tersimpan di URL → bisa di-bookmark
  & dibagikan).

### C4 — Observability ringan
- Halaman "Status" tersembunyi: versi data, jumlah saham, waktu build, error
  terakhir refresh.

## 8. Pagar metodologi (tetap mengikat — dari v1.1)

1. **Hanya momentum & growth yang menggerakkan peringkat.** Semua tambahan v2
   (valuasi, target, berita, kalender laba, indeks) adalah **konteks**.
2. **Point-in-time** dipertahankan untuk semua fundamental.
3. **Survivorship bias & "bukan saran investasi"** selalu diungkap di UI.
4. **Penambahan sinyal penggerak** wajib backtest OOS lolos dulu.

## 9. Risiko & mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| GitHub Action gagal/diam | Data basi diam-diam | Badge umur data + notifikasi gagal via status Action |
| Universe 500 → memori jebol di free tier | App crash/OOM | B3: Parquet tunggal, potong horizon, lazy load |
| Update Streamlit memecah chart | App error | C1 pin versi; uji sebelum bump |
| `query_params` watchlist terbatas panjang URL | Watchlist besar putus | Batasi + opsi ekspor/impor teks (A2) |
| Rate-limit SEC saat universe besar | Unduhan gagal | Throttle + inkremental (sudah ada di edgar_client) |
| Yahoo ubah skema field | Kolom kosong | C2 degradasi anggun + cek sanity B6 |

## 10. Arsitektur (perubahan)

```
.github/workflows/update-data.yml   (BARU)  # cron unduh+commit data
app.py                               # responsif, watchlist, compare, preset
src/stocks/
├── signals.py        # + kolom baru (FCF, buyback, gross margin)
├── market_context.py (BARU)  # indeks pembanding, kalender laba
├── watchlist.py      (BARU)  # baca/tulis watchlist via query_params
└── ... (tetap)
data/
├── prices.parquet    (BARU, ganti 300+ CSV)  # B3
├── fundamentals.csv
└── edgar_normalized.parquet
requirements.txt       # versi dipin (C1)
docs/PRD_app_roadmap.md
```

## 11. Milestone (urut prioritas dampak/usaha)

| M | Isi | Kriteria selesai |
|---|---|---|
| M1 | C1 pin versi + C2 degradasi anggun | App tak pernah blank; versi terkunci |
| M2 | B1 auto-update GitHub Actions | Action mingguan hijau; data ter-commit otomatis |
| M3 | A1 responsif + A4 onboarding | Terbaca di 390px; panel edukasi ada |
| M4 | A2 watchlist + A5 preset + ekspor CSV | Favorit & preset jalan, tersimpan di URL |
| M5 | B2+B3 universe 300–500 + Parquet | ≥300 saham, RAM < 700 MB |
| M6 | A3 compare + B5 konteks pasar (indeks, kalender laba) | Banding & acuan indeks tampil |
| M7 | B4 data lebih dalam + A6 tema/IDR + C4 status | Metrik baru, tema, halaman status |

Urut wajib M1→M2 dulu (keandalan & kesegaran = fondasi); sisanya bisa diatur
ulang sesuai kebutuhan. Tiap milestone diverifikasi (uji render + cek data).

## 12. Pertanyaan terbuka (jawab sebelum mulai)

1. **Auto-update: mingguan cukup, atau harian?** *(default: mingguan Senin;
   EDGAR bulanan)*
2. **Universe target: S&P 500 penuh atau ~300 likuid dulu?** *(default: ~300
   dulu — aman untuk memori, perluas bertahap)*
3. **Watchlist: cukup via URL (bookmark) atau perlu ekspor/impor file?**
   *(default: URL + ekspor teks)*
4. **Tampilkan estimasi harga IDR?** *(default: ya, berlabel "perkiraan kurs")*
5. **Prioritas pertama dikerjakan: keandalan (M1–M2) atau fitur UI (M3–M4)?**
   *(default: M1–M2 dulu — data segar & tak crash lebih penting)*
