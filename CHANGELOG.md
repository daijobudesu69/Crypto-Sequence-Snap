# Changelog

Setiap perubahan yang menyentuh parameter strategi, aturan eksekusi, atau cara
pencatatan dicatat di sini **dengan tanggal dan alasan** — forward test hanya
bisa dibaca kalau setiap baris log bisa dicocokkan dengan aturan yang berlaku
saat itu (`engine_version` di tiap baris).

## snap-v2-fwd-1.4.0 — 2026-11-22

5 trade selesai (semua stop), tidak ada posisi terbuka saat perubahan ini.
**Parameter strategi tidak berubah** — yang berubah biaya paper dan pemantau.

- **Slippage paper = backtest.** 1 tick per sisi melawan posisi (`paper.slippage_ticks`
  di config.yaml): entry = open + tick, exit = level/open − tick, qty dari fill
  setelah slippage — sama dengan `engine.py` riset. Tick per koin = tick yang
  dipakai backtest (`datafeed.TICK`; riset `derive_tick_size`, NEAR dari data lake).
- **Funding dipotong.** Tiap EXIT: funding perp yang dibayar selama posisi
  terbuka, rumus dan jendela sama dengan riset `funding.biaya_per_trade`
  (entry_bar < t ≤ exit_bar, notional = qty × close bar 4H yang memuat t).
  Tarif dari riwayat Gate.io perp — Binance fapi tetap HTTP 451 dari runner;
  tracking error yang sama jenisnya dengan candle. Gate gagal → bar exit diulang
  di siklus berikutnya; setelah 6 jam ditulis `funding_source = tidak_tersedia`.
- `R_realisasi` = R kotor − komisi − funding (= R bersih backtest). Kolom baru di
  `trades.csv`: `funding_R`, `funding_n`, `funding_source`, `tick_size`,
  `komisi_R`; kolom template `slippage_*_tick` dan `funding_dibayar_usd` kini terisi.
- **5 trade lama dihitung ulang** dengan rumus yang sama (`tools/restate_costs.py`):
  total −5,124 R → −5,153 R (funding +0,002 s/d +0,007 R per trade; slippage
  ≤ 0,003 R). `events.csv` lama tidak diubah (log mentah).
- **Pemantau estafet** (signal.yml): menyalakan penggantinya sendiri saat
  anggaran waktu habis, dan tidak pernah serah terima tepat di atas tutup lilin.
  Alasan: 1–21 Nov terukur 34 jeda 1,3–4,8 jam, semuanya mulai saat pemantau
  habis anggaran lalu menunggu cron yang telat. Sekalian: siklus yang gagal tidak
  lagi mematikan pemantau (`bash -e` + `rc=$?` dulu langsung keluar).

## snap-v2-fwd-1.3.0 — 2026-09-27

Belum ada trade.

- **Template sinyal Telegram ditetapkan Dew** (ringkas: entry, harga acuan,
  stop, target, ukuran posisi). Baris peringatan hanya muncul bila pesan
  terlambat > 15 menit atau tertahan di antrean > 10 menit.
- **Cermin Google Sheets** lewat service account (disalin dari MEX): tiap baris
  events/trades/runs juga ditulis ke tab bernama sama. Gagal ke Sheets tidak
  pernah menghalangi CSV. `runs.csv` mendapat kolom `sheet` (status cermin
  per run) — header berubah, jadi log lama diarsipkan ke `runs.v1.csv`.

## snap-v2-fwd-1.2.0 — 2026-09-27

Belum ada trade.

- **Watchlist final 6 koin: ETH, BNB, XRP, DOGE, AVAX, NEAR.** Keputusan Dew
  setelah melihat perbandingan sumber data per koin.
- **TRX dan TAO dikeluarkan** (dipantau ~25 menit, nol sinyal, nol posisi).
  Alasan: kecocokan sinyal sumber terbaiknya hanya 66,7% terhadap Binance
  futures — tracking data, BUKAN hasil backtest-nya. Slot state keduanya
  dibiarkan di position.json (kosong, tidak diproses).
- Frekuensi ~3,5–4 trade/bulan → 100 trade ≈ 2–2,5 tahun.

## snap-v2-fwd-1.1.0 — 2026-09-27

Belum ada trade (belum ada sinyal sejak mulai).

- **Watchlist + TRX, NEAR, TAO** (8 koin). Permintaan Dew; Report 10.1
  menyarankan 8–15 koin karena 5 koin butuh ~2,5–3 tahun untuk 100 trade.
  Belum dipastikan apakah ketiganya bagian dari universe 15 koin riset.
- **XMR ditahan**: kecocokan sinyal sumber terbaiknya (Gate perp) hanya 37,5%
  terhadap Binance futures, dan Binance spot sudah tidak memperdagangkan XMR.
  Alasan penahanan adalah tracking data, BUKAN hasil backtest-nya.
- **Sumber data dipilih per koin** (`snap/datafeed.py` PRIMARY), dari pengukuran
  `docs/SPOT_VS_PERP.md` 27 Sep 2026. Aturan pilih ditetapkan sebelum hasil
  dilihat: kecocokan sinyal tertinggi, seri → beda harga 90 hari terkecil.
  Hasil: ETH/BNB/XRP → Binance spot; DOGE/AVAX/TRX/NEAR/TAO → Gate.io perp.
  DOGE dan AVAX berpindah sumber (tanpa posisi terbuka, tidak ada yang terputus).
- Kunci `prefer_source` di config.yaml dihapus dan kini ditolak — sumber per
  koin tinggal di satu tempat.

## snap-v2-fwd-1.0.0 — 2026-09-26

Repo dibuat. Belum ada trade.

- **Versi 2** dipilih (pola + RSI + EMA200), menggantikan pilihan awal Versi 1,
  sebelum trade pertama. Alasan: Versi 1 gagal out-of-sample 2021–2023
  (t = −0,07). Setup V1 diarsipkan di `docs/arsip/`.
- **Paper trading**, modal kertas **$300**, risiko 1% modal awal ($3/trade),
  komisi 0,05% per sisi. Funding dan slippage tidak dimodelkan.
- Watchlist ETHUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, AVAXUSDT, 4H.
- Parameter strategi = Report 4.3, tidak ada yang diubah:
  run 5, toleransi 0,05%, RSI 14 > 40 dan naik, EMA 200, target 1,5R, long saja.
- Data: Binance spot mirror (utama), Gate.io perp (cadangan) — backtest memakai
  Binance perp. Tracking error diukur oleh `tools/measure_spot_vs_perp.py`.
- Telegram: kode siap, secret menyusul. Google Sheets: belum ada.
