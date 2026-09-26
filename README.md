# Crypto-Sequence-Snap — Forward Test Versi 2

Forward test **paper trading** untuk strategi **Sequence Snap Versi 2** (pola +
RSI + EMA200) di **ETHUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, AVAXUSDT**, timeframe 4H,
modal kertas **$300**. Bot di GitHub Actions mengecek ~45 detik setelah tiap
lilin 4H tutup, mengeksekusi di atas kertas, mengirim sinyal ke Telegram
**hanya kalau ada**, dan mencatat semuanya ke CSV di repo ini.

> [!WARNING]
> **Strategi ini DITOLAK untuk uang sungguhan. Conviction 20%.**
> Versi 1 gagal di uji out-of-sample 2021–2023 (t = −0,07). Versi 2 bertahan
> (t = 1,99), tapi filter EMA200-nya sendiri tidak lolos uji formal
> (Bonferroni p = 0,200). Forward test ini adalah ujian bersih pertamanya —
> **bukan** strategi yang sudah terbukti.
>
> Semua bukti: [`docs/Sequence Snap Report Trading Strategy.md`](docs/Sequence%20Snap%20Report%20Trading%20Strategy.md)
> · jejak keputusan riset: [`docs/PROJECT_LOG_Sequence-Snap.md`](docs/PROJECT_LOG_Sequence-Snap.md)
> · setup forward test: [`docs/FORWARD_TEST_V2_SETUP.md`](docs/FORWARD_TEST_V2_SETUP.md)

---

## Aturan strategi

Dievaluasi saat lilin 4H **tutup**. Eksekusi di **open lilin berikutnya**.

```
 bar 5    bar 4    bar 3    bar 2    bar 1    bar 0
[MERAH]  [hijau]  [hijau]  [hijau]  [hijau]  [hijau]  →  ENTRY di open lilin berikutnya
```

| # | Syarat | Rumus |
|---|---|---|
| 1 | Bar 5 merah | `close[5] < open[5]` |
| 2 | Bar 0–4 hijau | `close[i] > open[i]` |
| 3 | Tidak turun ke dasar lilin merah | `low[i] > low[5]` (sama persis = gagal) |
| 4 | Tiap close naik, toleransi 0,05% | `close[i] > close[i+1] × 0,9995`, **i = 0..3 saja** |
| 5–6 | Momentum | `RSI(14) > 40` dan `RSI[0] > RSI[1]` (RSI Wilder/RMA) |
| 7 | Posisi kosong di koin itu | — |
| **8** | **Versi 2: tren** | **`close[0] > EMA200`** |

| | |
|---|---|
| Stop | `low[5]` — beku, tidak ada trailing |
| Target | `close[0] + 1,5 × (close[0] − low[5])` |
| Exit | Stop atau target. Kena dua-duanya di lilin sama → stop. Tidak ada batas waktu |
| Qty | `($300 × 1%) ÷ (entry − stop)` |
| Dilarang | Short, trailing, filter tambahan, mengubah 1,5R (Report 4.2) |

`snap/strategy.py` adalah salinan baris-per-baris dari `strategy.py` riset
(yang sudah lolos 65 test dan replikasi TradingView) plus syarat #8.
`tests/test_strategy.py` mengadu keduanya langsung, jadi tidak bisa menyimpang
diam-diam.

---

## Cara kerja

```
cron (tiap 30 mnt)
  └─ menyalakan pemantau yang hidup ~5,5 jam
       └─ tiap 10 menit + 45 detik setelah tiap lilin 4H tutup:
            refresh_state.sh  → tarik state terbaru
            run_signal.py     → proses bar baru → antre pesan → kirim Telegram
            run_heartbeat.py  → 1 pesan/hari, 07:00 WIB
            save_state.sh     → commit state/ ke repo (retry + merge by content)
```

Polanya diambil dari [Crypto-MEX](https://github.com/daijobudesu69/Crypto-MEX),
termasuk semua pengaman yang lahir dari insidennya: pemantau panjang karena cron
GitHub hanya jalan 23–26%, outbox + `sent_ids` supaya pesan tidak hilang atau
dobel, `last_bar` yang hanya maju, dan state yang digabung berdasarkan isi.

**Beda dari MEX:** pemantau juga bangun tepat ~45 detik setelah tiap lilin
tutup, bukan hanya tiap 10 menit. Entry Sequence Snap adalah open lilin
berikutnya — yang menentukan adalah jeda setelah tutup.

---

## Sumber data — dan tracking error-nya

Backtest memakai **Binance USD-M perp**. `fapi.binance.com` menjawab **HTTP 451**
dari runner GitHub (IP AS diblokir), jadi bot memakai:

1. `data-api.binance.vision` — **Binance spot**, utama
2. `api.gateio.ws` — Gate.io perp, cadangan otomatis

Ini tracking error nyata. Besarnya per koin diukur oleh workflow
**"Ukur spot vs perp"** → [`docs/SPOT_VS_PERP.md`](docs/SPOT_VS_PERP.md)
(dibuat saat workflow itu pertama dijalankan). Sumber yang dipakai dicatat di
setiap baris log.

Bot mengambil **1.500 bar** per koin (bukan 1.000 seperti MEX) supaya EMA200
terbentuk penuh: sisa pengaruh nilai awal EMA di 1.500 bar ~0,00003%.

---

## Menyalakan

1. **Actions → "Ukur spot vs perp" → Run workflow.** Wajib hijau sebelum mulai:
   ia mereplikasi contoh Report Bagian 3 dengan mesin repo ini.
2. **Pemantau sinyal jalan otomatis** lewat cron begitu repo ini ada di GitHub.
   Run pertama tiap koin **bootstrap flat**: mengambil lilin terbaru dan mulai
   dari sana, tanpa memutar ulang sejarah.
3. **Telegram (menyusul).** Settings → Secrets and variables → Actions → New
   repository secret:
   - `TELEGRAM_BOT_TOKEN` — dari @BotFather
   - `TELEGRAM_CHAT_ID` — id chat Anda

   Lalu jalankan workflow **"Kirim pesan tes"**. Selama secret kosong, pesan
   dicetak ke log job dan forward test tetap tercatat di CSV.
4. **Google Sheets (menyusul).** Belum ada di repo ini. CSV di `state/` adalah
   catatan resmi.

---

## Pesan Telegram

| Pesan | Kapan |
|---|---|
| 🟢 **SEQUENCE SNAP v2 — LONG** | Sinyal terbentuk. Close, stop, target, qty untuk $300, RSI, jarak ke EMA200 |
| 📌 **ENTRY TERCATAT (paper)** | Lilin berikutnya buka — harga entry referensi |
| ✅ / 🛑 **EXIT** | Target / stop kena. R bersih, $ paper, total, kalah beruntun |
| 💓 **hidup** | 1× sehari 07:00 WIB. Posisi, progres x/100 trade, drawdown |
| 🚨 **ATURAN BERHENTI TERPICU** | Di EXIT/heartbeat kalau salah satu aturan §6 setup tercapai |

---

## Isi repo

| Path | Isi |
|---|---|
| `snap/strategy.py` | 8 syarat entry + mesin posisi paper |
| `snap/datafeed.py` | Data 4H, 5 koin (watchlist dikunci di sini) |
| `snap/notify.py` | Template dan pengiriman Telegram |
| `snap/stats.py` | Ringkasan + pemeriksaan aturan berhenti |
| `run_signal.py` / `run_heartbeat.py` | Driver yang dipanggil workflow |
| `config.yaml` | Parameter terkunci + modal kertas |
| `state/` | **Bukti forward test**: `trades.csv`, `events.csv`, `runs.csv`, `position.json` |
| `forward_test_log.csv` | Template untuk fill manual Anda (opsional) |
| `pine/SequenceSnap_v2.pine` | Script TradingView untuk verifikasi visual |
| `tools/measure_spot_vs_perp.py` | Ukur tracking error + replikasi Report |
| `tests/` | Parity dengan kode riset, 8 syarat, mesin posisi, pipa kirim |
| `docs/` | Report, project log, setup V2, arsip setup V1 |

```bash
pip install -r requirements.txt
python tests/test_strategy.py     # strategi — harus hijau
python tests/test_infra.py        # pipa kirim — harus hijau
```

---

## Aturan berhenti (disepakati sebelum trade pertama)

| Kondisi | Tindakan |
|---|---|
| Drawdown kertas menembus **−20%** | Berhenti, evaluasi ulang |
| **15 kekalahan beruntun** | Berhenti (rekor historis 12) |
| **100 trade**, expectancy ≤ 0 | Strategi ditolak |
| Sinyal live tidak cocok dengan 8 syarat | Hentikan, cari sebabnya |

Frekuensi V2 di 5 koin ~3 trade/bulan, jadi **100 trade ≈ 2,5–3 tahun**.
Acuan jujurnya Versi 3 (out-of-sample): **+0,19 R/trade, win rate ~49%**.
