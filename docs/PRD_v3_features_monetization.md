# PRD — US Stock Monitor v3.0 (Fitur Lanjutan & Monetisasi)

**Versi:** 3.0 · **Tanggal:** 2026-06-15 · **Status:** Draft untuk persetujuan
**Repo:** github.com/JohnAprek/us-stock-monitor
**Melanjutkan:** PRD_app_roadmap v2.0 (selesai, M1–M7)

---

## 1. Ringkasan & posisi sekarang

Setelah v2.0, aplikasi adalah **alat riset saham US gratis & jujur**: meranking
~493 saham S&P 500 (momentum + growth tervalidasi), dengan fundamental mendalam,
target analis, return, dividen, berita, kalender laba, watchlist, banding,
preset, ekspor, tema gelap — auto-update mingguan, ~7 MB data, live di web.

v3.0 menjawab dua pertanyaan berbeda:
1. **Fitur** — apa yang membuat pengguna kembali tiap hari & merasa butuh?
2. **Monetisasi** — bagaimana menutup biaya dan (mungkin) menghasilkan, **tanpa
   merusak kepercayaan** yang jadi inti produk ini?

**Prinsip non-negosiasi v3.0:** monetisasi TIDAK boleh memengaruhi peringkat.
Tidak ada bayar-untuk-naik-peringkat, tidak ada bias afiliasi pada rekomendasi.
Uang datang dari *kenyamanan & kedalaman*, bukan dari menjual posisi ranking.

## 2. Dua kebenaran yang harus dihadapi sebelum monetisasi

Sebelum membahas fitur berbayar, dua isu hukum/operasional WAJIB diputuskan —
mengabaikannya membuat seluruh model bisnis rapuh:

### 2.1 Lisensi data (KRITIS)
Data harga & fundamental saat ini dari **Yahoo Finance via `yfinance`**. ToS
Yahoo **melarang penggunaan/redistribusi komersial**. Untuk produk **gratis
personal** ini wilayah abu-abu yang ditoleransi; untuk produk **berbayar**, ini
risiko hukum nyata dan sumber data bisa diputus sewaktu-waktu.
- **SEC EDGAR** (fundamental point-in-time) = domain publik, **aman komersial**.
- **Harga & data analis** untuk versi berbayar perlu **penyedia berlisensi**:
  Tiingo (~$10/bln), Financial Modeling Prep, Polygon.io, IEX, EOD Historical
  Data. Biaya ini masuk ke unit economics (§6.4).
- **Keputusan:** versi berbayar HARUS pindah ke sumber data berlisensi sebelum
  diluncurkan. Versi gratis boleh tetap yfinance dengan disclaimer.

### 2.2 Regulasi nasihat keuangan (KRITIS)
Menarik bayaran untuk "rekomendasi saham" bisa masuk kategori **penasihat
investasi** (di AS: SEC/RIA; di Indonesia: OJK). Mitigasi posisi produk:
- Tetap sebagai **"alat riset & penyaring data"**, BUKAN "saran beli personal".
- Tidak ada saran yang disesuaikan profil/keuangan individu (itu pemicu regulasi).
- Disclaimer permanen "bukan nasihat investasi" di setiap tier.
- Hindari klaim performa/janji return dalam materi pemasaran.

## 3. Tujuan & metrik sukses

| # | Tujuan | Metrik |
|---|--------|--------|
| G1 | Retensi harian | ≥ 30% pengguna mingguan kembali ≥ 3×/minggu |
| G2 | Fitur "wajib kembali" | Alert terkirim & diklik; watchlist aktif per pengguna |
| G3 | Fondasi multi-user | Akun + persistensi (watchlist/portfolio) per pengguna |
| G4 | Monetisasi sehat | Konversi free→pro ≥ 2–4%; pendapatan menutup biaya data+hosting |
| G5 | Kepercayaan utuh | NOL keluhan "ranking dijual"; disclosure jelas di semua kanal |

## 4. Non-goals v3.0

- ❌ Eksekusi order / jadi broker (selamanya manual)
- ❌ Nasihat investasi personal (memicu regulasi)
- ❌ Bayar-untuk-peringkat / sponsor memengaruhi skor
- ❌ Pindah dari pendekatan "hanya sinyal tervalidasi yang menggerakkan ranking"
- ❌ Janji/garansi return dalam pemasaran

## 5. Epic fitur

### F1 — Alert & notifikasi (pendorong retensi utama)
- Pemicu: saham watchlist masuk "Direkomendasikan", skor naik/turun signifikan,
  laba ≤ 3 hari, harga tembus 52-mgg, breakout momentum.
- Kanal: **email** (gratis via SMTP/Resend), **Telegram bot** (gratis), push PWA.
- Frekuensi: harian ringkas + alert real-time (sesuai tier).
- *Monetisasi:* gratis = 1 alert/minggu ringkasan; Pro = real-time tak terbatas.

### F2 — Pelacakan portofolio
- Input holdings (ticker, lot, harga beli) → P/L, P/L vs SPY (jujur: apakah
  mengalahkan indeks), eksposur momentum/growth portofolio, konsentrasi sektor.
- Saran rebalancing berbasis skor (dengan disclaimer, bukan perintah).
- *Monetisasi:* gratis = 1 portofolio ≤ 10 posisi; Pro = tak terbatas + riwayat.

### F3 — Asisten riset AI (diferensiasi premium)
- Pakai **Claude API** (claude-opus/sonnet) untuk: ringkas berita per saham,
  ringkas laporan laba/transkrip, jelaskan "mengapa skor ini" dalam bahasa awam,
  bandingkan 2 saham naratif, tanya-jawab atas data fundamental yang sudah ada.
- **Pagar:** AI menjelaskan/menyimpulkan DATA yang ada — tidak menciptakan sinyal
  ranking baru, tidak memberi "nasihat beli". Output selalu berlabel + disclaimer.
- *Monetisasi:* fitur Pro (biaya token nyata → harus tier berbayar). Batas kuota.

### F4 — Sinyal & universe tambahan (lewat gerbang validasi)
- Universe: NASDAQ-100, ETF sektor, mid-cap (Russell), kustom dari watchlist.
- Kandidat sinyal baru (mis. momentum relatif-sektor, kualitas-momentum) —
  **wajib backtest OOS lolos** sebelum jadi penggerak (pagar metodologi v1.1).
- *Monetisasi:* gratis = S&P 500; Pro = semua universe + sinyal lanjutan.

### F5 — Akun pengguna & persistensi (fondasi monetisasi)
- Auth (email magic-link / OAuth Google). Database per-pengguna (watchlist,
  portfolio, alert, pengaturan, tier).
- Migrasi dari Streamlit single-user → multi-user. Lihat §7 arsitektur.

## 6. Monetisasi

### 6.1 Model: Freemium SaaS
| | **Gratis** | **Pro (~$8–15/bln)** | **Premium (~$25–40/bln)** |
|---|---|---|---|
| Universe | S&P 500 | + NASDAQ-100, sektor, mid-cap | + kustom & internasional |
| Ranking momentum+growth | ✅ | ✅ | ✅ |
| Watchlist | 1, via URL | tak terbatas, tersimpan | tak terbatas |
| Alert | mingguan ringkas | real-time tak terbatas | + prioritas |
| Portofolio | 1 (≤10 posisi) | tak terbatas + riwayat | + analitik lanjutan |
| Asisten AI | — | kuota terbatas | kuota besar |
| Data | tertunda/EOD | EOD berlisensi | intraday (jika layak) |
| Ekspor & API | CSV | + akses API terbatas | + API penuh |

### 6.2 Jalur pendapatan
1. **Langganan (utama)** — Stripe; bulanan & tahunan (diskon tahunan).
2. **Afiliasi broker** (sekunder, HATI-HATI) — referral broker saham US yang
   bisa diakses dari ID. **Wajib:** disclosure jelas + TIDAK memengaruhi ranking
   + ditempatkan di area "cara eksekusi", bukan di rekomendasi.
3. **Akses API** — jual data ranking ke developer/komunitas (tier Premium/B2B).
4. **Donasi** ("traktir kopi") — kanal gratis, ekspektasi rendah, jaga goodwill.
5. **B2B / white-label** (jangka panjang) — lisensi ke komunitas/edukator finansial.

### 6.3 Yang DIHINDARI (merusak kepercayaan)
- ❌ Iklan saham / "sponsored picks" di daftar
- ❌ Bayar agar saham muncul lebih tinggi
- ❌ Afiliasi yang membiaskan urutan/skor
- ❌ Menjual data pengguna

### 6.4 Unit economics (estimasi jujur, bulanan)
- **Biaya:** data berlisensi ~$10–50, hosting (Render/Fly/Railway) ~$7–25,
  database ~$0–15, Claude API (variabel, dibatasi kuota) ~$X, email/Telegram ~$0.
  Total dasar ~$25–90/bln sebelum skala.
- **Titik impas kasar:** ~5–10 pelanggan Pro menutup biaya dasar.
- **Realita jujur:** konversi freemium tipikal 2–4%; butuh ribuan pengguna gratis
  untuk pendapatan berarti. Ini proyek pertumbuhan jangka panjang, bukan cepat
  kaya — selaras dengan etos jujur produk ini.

## 7. Arsitektur untuk multi-user & monetisasi

```
Sekarang (v2):  Streamlit single-user + data file di repo + auto-update Action
v3 (bertahap):
  Frontend     : Streamlit (cepat) ATAU migrasi ke web app (Next.js) bila perlu
  Auth         : magic-link / OAuth (mis. Supabase Auth, Clerk)
  Database     : Postgres (Supabase/Neon) — user, watchlist, portfolio, alert, tier
  Payments     : Stripe (checkout, webhook, billing portal)
  Data layer   : penyedia berlisensi (harga/analis) + SEC EDGAR (fundamental)
  Jobs         : cron (data refresh, evaluasi alert) — GitHub Actions / worker
  AI           : Claude API dengan kuota & caching per pengguna
  Hosting      : Render/Fly/Railway (Streamlit free tier tak cukup multi-user)
```
**Catatan:** Streamlit cukup untuk MVP berbayar (dengan auth + Stripe), migrasi
ke framework web penuh hanya bila UX/skala menuntut.

## 8. Risiko & mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| ToS data Yahoo (komersial) | Sumber diputus / masalah hukum | §2.1 pindah ke data berlisensi untuk tier berbayar |
| Regulasi penasihat investasi | Sanksi/penutupan | §2.2 posisikan sebagai alat data, disclaimer, no personalized advice |
| Monetisasi merusak kepercayaan | Pengguna kabur | §6.3 pagar etika; disclosure; ranking tak tersentuh uang |
| Biaya AI membengkak | Margin negatif | Kuota per tier + caching + model sesuai tugas (Haiku/Sonnet untuk ringkas) |
| Konversi rendah | Pendapatan tak menutup biaya | Mulai biaya rendah; fitur gratis tetap kuat untuk pertumbuhan organik |
| Beban multi-user di hosting | Lambat/mahal | Mulai kecil (Render), skalakan saat ada pelanggan |
| Churn | Pendapatan tidak stabil | Alert & portofolio = pengikat harian; tagihan tahunan |

## 9. Pagar metodologi & etika (mengikat, dari v1.1 + baru)

1. Hanya **momentum & growth tervalidasi** yang menggerakkan ranking.
2. **Uang tidak pernah menyentuh peringkat** — no pay-to-rank, no biased affiliate.
3. **Point-in-time** dipertahankan; **survivorship bias** diungkap.
4. Sinyal baru wajib **backtest OOS lolos** sebelum jadi penggerak.
5. AI hanya **menjelaskan data**, tidak menciptakan sinyal/nasihat.
6. **Bukan nasihat investasi** — disclaimer di semua tier & materi pemasaran.
7. **Transparansi monetisasi** — afiliasi & batasan diungkap jelas.

## 10. Milestone (urut: validasi bisnis → fondasi → fitur → bayar)

| M | Isi | Kriteria selesai |
|---|---|---|
| M1 | **Keputusan strategis** — data berlisensi & posisi regulasi (§2) | Sumber data komersial dipilih; disclaimer & positioning final |
| M2 | F1 Alert (email/Telegram) di app gratis sekarang | Alert watchlist & laba terkirim; uji retensi |
| M3 | F5 Akun + DB + persistensi (watchlist/portfolio) | Login jalan; data per-pengguna tersimpan |
| M4 | F2 Portofolio + vs SPY | P/L & vs-indeks per pengguna tampil |
| M5 | Stripe + tiering (gratis/Pro) + gating fitur | Checkout & batas tier berfungsi |
| M6 | F3 Asisten AI (Claude) sebagai fitur Pro | Ringkasan/QA berkuota jalan; biaya terkendali |
| M7 | F4 universe & sinyal tambahan (tervalidasi) | Universe baru + sinyal lolos backtest |

Urutan sengaja menaruh **M1 (keputusan data/regulasi) paling depan** — tanpa itu,
membangun fitur berbayar di atas data tak-berlisensi adalah membangun di pasir.
Alert (M2) bisa jalan lebih dulu di app gratis untuk menguji retensi sebelum
investasi besar ke akun/billing.

## 11. Pertanyaan terbuka (jawab sebelum M1)

1. **Tujuan utama:** proyek pribadi yang ditingkatkan, atau benar-benar bisnis?
   *(menentukan seberapa jauh investasi data/regulasi)*
2. **Anggaran biaya bulanan** yang siap ditanggung sebelum ada pendapatan?
   *(menentukan pilihan data/hosting)*
3. **Target pasar:** investor ritel Indonesia, global, atau komunitas spesifik?
4. **Harga & mata uang langganan** — USD global (Stripe) atau lokal?
5. **Afiliasi broker:** dipakai atau dihindari demi kemurnian?
   *(default: hindari di awal; pertimbangkan nanti dengan disclosure ketat)*
6. **AI:** prioritas tinggi (diferensiasi) atau nanti? *(default: M6, setelah
   fondasi berbayar siap)*
