# Monetization Launch Playbook — Lean Validation ($0 fixed cost)

**Tanggal:** 2026-06-15 · **Keputusan:** bisnis, validasi-dulu, pasar global (Inggris)
**Melanjutkan:** PRD v3.0 §6 (monetisasi)

Tujuan dokumen ini: cara menghasilkan uang pertama **tanpa biaya tetap** dan
**tanpa membangun SaaS penuh** — menguji apakah orang mau bayar sebelum
berinvestasi besar. Selaras dengan etos proyek: **validasi sebelum komitmen.**

---

## 1. Model: paid newsletter (digest premium)

- **Produk gratis (corong):** app publik Streamlit + Free Weekly Digest
  (`data/digest_free.md`) — menarik orang, menunjukkan nilai, mengajak langganan.
- **Produk berbayar:** Premium Digest (`data/latest_digest.md`) — top 10 lengkap
  + skor + harga + target analis + perubahan peringkat + alert laba, mingguan.
- **Mengapa newsletter, bukan SaaS dulu:** $0 biaya tetap, tanpa akun/DB/Stripe,
  tanpa eskalasi lisensi data (ini *komentar riset*, bukan jual-ulang feed data).

## 2. Pilih platform pembayaran+pengiriman (semua $0 tetap)

| Platform | Biaya | Kelebihan | Kekurangan |
|---|---|---|---|
| **Substack** | ~10% per penjualan | Termudah, audiens bawaan, kelola email+bayar | Branding Substack, 10% |
| **Beehiiv** | Free tier + ~ saat skala | Lebih pro, analitik, referral | Sedikit lebih kompleks |
| **Gumroad** | ~10% + fee | Cocok produk/membership | Bukan native email berkala |
| **Ghost** | $9/bln (hosting) | Milik sendiri, no cut | Ada biaya tetap |

**Rekomendasi awal: Substack** — gesekan paling rendah untuk validasi, $0 tetap,
hanya potong saat Anda benar-benar menjual. Pindah ke Beehiiv/Ghost saat tumbuh.

## 3. Harga (pasar global, USD)

- **Free:** digest mingguan ringkas (teaser) — selamanya gratis (corong).
- **Premium:** **$7/bln** atau **$60/th** (hemat ~30%). Titik harga umum untuk
  newsletter investasi ritel; cukup rendah untuk konversi, cukup untuk berarti.
- Mulai lebih murah ($5) saat peluncuran (early-bird) untuk membangun bukti
  sosial (jumlah pelanggan), naikkan kemudian.

## 4. Positioning & disclaimer (WAJIB — lindungi diri)

- Tagline: *"A momentum + growth screener for S&P 500 — research, not advice."*
- Disclaimer permanen di setiap kiriman & halaman:
  > Research and educational tool only. Not investment advice. Not personalized
  > to your situation. You make and execute your own decisions. Past performance
  > and model rankings do not guarantee future results.
- **Jangan** janjikan return, **jangan** beri saran personal, **jangan** klaim
  "pasti profit". Ini menjaga posisi sebagai *alat data*, bukan penasihat (OJK/SEC).

## 5. Alur kerja mingguan (sudah 90% otomatis)

1. GitHub Action (Senin) refresh data + hasilkan `digest_free.md` &
   `latest_digest.md` (premium). **Sudah jalan.**
2. **Free** → publish sebagai post gratis di Substack (tempel, atau otomasi via
   API nanti) + kirim ke channel publik Telegram.
3. **Premium** → publish sebagai post berbayar di Substack (hanya pelanggan).
4. (Opsional) Telegram premium channel untuk pelanggan via secret bot.

Set link checkout Anda di env `SUBSCRIBE_URL` (atau secret GitHub) supaya teaser
gratis otomatis menautkan ke halaman langganan.

## 6. Metrik validasi (kapan dianggap "terbukti")

- **Target 60 hari:** ≥ 10 pelanggan berbayar **atau** ≥ 100 pelanggan gratis
  dengan konversi ≥ 3%. Ini sinyal cukup untuk investasi tahap berikutnya.
- **Jika tercapai →** baru bangun jalur SaaS (akun + Stripe + data berlisensi +
  AI) per PRD v3.0 M3–M6.
- **Jika tidak →** murah untuk diketahui sekarang; iterasi produk/positioning,
  bukan menghabiskan ribuan dolar dulu. (Pelajaran yang sama dengan strategi
  trading: gagal cepat & murah > gagal lambat & mahal.)

## 7. Distribusi (cara dapat pembaca gratis — pasar global)

- Reddit: r/investing, r/stocks, r/SecurityAnalysis (bagikan analisis, bukan spam).
- Twitter/X & StockTwits: posting top-pick mingguan + grafik, link ke free digest.
- Bagikan **app gratis** sebagai alat berguna (link bisa di-bookmark via URL).
- Konsistensi mingguan > viral sekali. Newsletter tumbuh dari kepercayaan.

## 8. Checklist langkah pertama (semua $0)

- [ ] Buat akun **Substack** (gratis), nama & tagline + disclaimer (§4).
- [ ] Set harga Premium ($5 early-bird → $7).
- [ ] Set `SUBSCRIBE_URL` ke link Substack Anda (env/secret).
- [ ] Publish 2–3 **free digest** dulu (bangun kredibilitas) sebelum berbayar.
- [ ] Posting di 2–3 kanal distribusi (§7), konsisten tiap minggu.
- [ ] Pantau: pelanggan gratis, konversi berbayar, engagement. Tinjau di 60 hari.

## 9. Yang TIDAK dilakukan dulu (hindari bakar uang/risiko)

- ❌ Bangun akun + database + Stripe sebelum ada bukti permintaan.
- ❌ Beli data berlisensi mahal sebelum ada pelanggan.
- ❌ Janji return / saran personal (risiko regulasi).
- ❌ Jual-ulang feed data mentah (itu butuh lisensi; newsletter analisis tidak).
- ❌ Bayar iklan sebelum funnel organik terbukti konversi.
