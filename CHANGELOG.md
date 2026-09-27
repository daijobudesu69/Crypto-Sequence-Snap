# Changelog

Setiap perubahan yang menyentuh parameter strategi, aturan eksekusi, atau cara
pencatatan dicatat di sini **dengan tanggal dan alasan** — forward test hanya
bisa dibaca kalau setiap baris log bisa dicocokkan dengan aturan yang berlaku
saat itu (`engine_version` di tiap baris).

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
