# Setup Forward Test — Sequence Snap Versi 2

**Versi:** 2 — pola + RSI + **EMA200** (syarat #8: `close > EMA200`)
**Watchlist:** ETH, BNB, XRP, DOGE, AVAX (sejak 26 Sep 2026) + NEAR (sejak 27 Sep 2026), USDT, 4H
**Uang:** **paper trading**, modal kertas **$300**, risiko 1% = **$3 per trade**
**Eksekusi:** otomatis oleh bot di GitHub Actions — lihat [README](../README.md)
**Disiapkan:** 26 September 2026

> Dokumen ini menggantikan [`arsip/FORWARD_TEST_V1_SETUP.md`](arsip/FORWARD_TEST_V1_SETUP.md).
> Versi 1 sempat dipilih karena return in-sample-nya lebih tinggi, lalu diganti
> ke Versi 2 sebelum trade pertama: Versi 1 **gagal** di uji out-of-sample
> 2021–2023 (t = −0,07), Versi 2 satu-satunya yang bertahan (t = 1,99).
>
> Tapi MA200 sendiri **tidak lolos** uji formal (Bonferroni p = 0,200), dan
> memilihnya *karena* ia selamat di OOS sudah memakai OOS untuk memutuskan.
> **Forward test ini adalah ujian bersih pertamanya.** Conviction keseluruhan
> tetap 20% (Report Bagian 10).

---

## 1. Checklist sebelum mulai

- [ ] Baca [Report](Sequence%20Snap%20Report%20Trading%20Strategy.md) Bagian 2 (8 syarat entry) dan Bagian 10 (rekomendasi)
- [x] Jalankan workflow **"Ukur spot vs perp"** — hijau 26 & 27 Sep 2026.
      Contoh Report Bagian 3 cocok persis; jumlah trade V1 185/186.
- [x] Sumber data dipilih per koin dari hasilnya (`docs/SPOT_VS_PERP.md`, §3 di bawah)
- [ ] (nanti) Isi secret `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID`, lalu jalankan
      workflow **"Kirim pesan tes"**
- [ ] (opsional) Pasang `pine/SequenceSnap_v2.pine` di TradingView untuk verifikasi visual
- [ ] Catat tanggal mulai — bot mencatatnya sendiri di baris `[bootstrap]` pertama
      di `state/runs.csv` dan di `state/position.json`
- [ ] Sepakati aturan berhenti di §6 SEBELUM trade pertama, bukan sesudah

---

## 2. Modal kertas $300

$300 adalah ambang di mana hampir semua sinyal bisa dieksekusi tanpa ditolak
MIN_NOTIONAL Binance (Report 6.3). Di bawah itu, sinyal ETH yang justru
penyumbang besar mulai tertolak.

| | Nilai |
|---|---|
| Modal kertas | $300 |
| Risiko per trade | 1% modal **awal**, tidak di-compound = **$3,00** |
| Qty | `$3 ÷ (harga entry − stop)` |
| Komisi | 0,05% per sisi (sama dengan backtest) |
| Funding | **tidak dihitung** (API perp tidak terjangkau) — Report: rata-rata +0,012 R/trade |
| Slippage | **tidak dihitung** — paper fill di open / di level stop-target persis |

### Acuan hasil (bukan janji)

Dari Report 6.3, modal $300, **15 koin** (bukan watchlist ini):

| | Versi 2 (2024–26, in-sample) | **Versi 3 = V2 di 2021–23 (out-of-sample)** |
|---|---:|---:|
| $300 setelah 1 tahun | $390,32 (+30,1%) | **$332,06 (+10,7%)** |
| Expectancy per trade | +0,2584 R | **+0,1915 R** |
| Win rate | 51,7% | 49,4% |
| Max drawdown | 20,55 R | 11,79 R |
| Kalah beruntun terpanjang | 12 | 7 |

**Yang tidak saya ketahui:** angka Versi 2 khusus untuk watchlist ini tidak ada
di Report. `docs/SPOT_VS_PERP.md` §3 menghitung V2 per koin di Binance futures
(Jul 2024 – Ags 2026) sebagai pengganti kasarnya — tetap in-sample, dan **tidak
boleh** dipakai untuk memilih koin (data snooping).

---

## 3. Bagaimana bot mengeksekusi (paper)

| Langkah | Aturan | Sumber |
|---|---|---|
| Sinyal | 8 syarat Report 2.2 dievaluasi saat lilin 4H **tutup** | `snap/strategy.py` |
| Entry | Harga **OPEN** lilin berikutnya | Report 2.3 |
| Stop | `low[5]` — beku, **tidak ada trailing** | Report 2.3 |
| Target | `close[0] + 1,5 × (close[0] − low[5])` — dari close sinyal, beku | Report 2.3 |
| Exit | Stop atau target, mana yang kena dulu. Dua-duanya di lilin sama → **stop** | Report 4.1 |
| Gap | Open sudah melewati stop/target → terisi di **open** | PROJECT_LOG asumsi F |
| Batas waktu | **Tidak ada** — posisi ditahan sampai stop/target | Report 4.1 |
| Posisi | Maks. 1 per koin, tidak ada pyramiding, **long saja** | Report 4.2 |

Bot mengecek ~45 detik setelah tiap lilin tutup, lalu mengirim sinyal ke
Telegram. Kalau Anda juga ingin mengeksekusi manual (paper di exchange / testnet),
isi `forward_test_log.csv` dengan harga fill Anda sendiri — bandingkan dengan
`state/trades.csv` milik bot (nama kolomnya sama).

### Tracking error yang harus diingat

Backtest memakai data **Binance futures**, yang diblokir dari runner GitHub
(HTTP 451). Bot memakai Binance spot atau Gate.io perp, **dipilih per koin**
menurut kecocokan sinyalnya dengan Binance futures:

| Koin | Sumber | Kecocokan sinyal |
|---|---|---:|
| ETH / BNB / XRP | Binance spot | 87,5% / 82,8% / 90,0% |
| DOGE / AVAX / NEAR | Gate.io perp | 100% / 90,0% / 92,9% |
| TRX / TAO / XMR | — | 66,7% / 66,7% / 37,5% — **tidak dipakai** |

Sumber yang benar-benar menjawab dicatat di setiap baris log.

---

## 4. Ekspektasi frekuensi

| Sumber | Trade/bulan, 6 koin |
|---|---:|
| V2 di Binance futures, per koin, Jul 2024 – Ags 2026 (`SPOT_VS_PERP.md` §3) | ~4,1 |
| V3 (out-of-sample 2021–23): 0,59 per koin | ~3,5 |

Rata-rata **~1 trade tiap 7–9 hari**. Filter EMA200 membuang ~37% trade Versi 1
(503 → 315), yaitu semua yang muncul saat harga di bawah EMA200 — jadi di bear
market bisa **berminggu-minggu tanpa sinyal**. Itu perilaku yang diharapkan,
bukan bot rusak (heartbeat harian yang membuktikan bot masih hidup).

**Sampel 100 trade butuh sekitar 2–2,5 tahun.** Evaluasi antara tiap 20–25
trade (~6 bulan) tetap berguna, tapi jangan memutuskan apa pun dari sana
kecuali aturan berhenti §6 terpicu.

---

## 5. Log

| File | Diisi oleh | Isi |
|---|---|---|
| `state/trades.csv` | bot | Satu baris per trade selesai. Kolom = `forward_test_log.csv` + provenance |
| `state/events.csv` | bot | SIGNAL / ENTRY / EXIT dengan snapshot RSI, EMA200, OHLC |
| `state/runs.csv` | bot | Bukti hidup tiap run, sumber data, status Telegram |
| `forward_test_log.csv` | Anda (opsional) | Fill manual Anda sendiri kalau ikut eksekusi |

Kolom yang sengaja dibiarkan kosong oleh bot: `slippage_entry_tick`,
`slippage_exit_tick`, `funding_dibayar_usd`. Tiga-tiganya hanya bisa diisi dari
eksekusi sungguhan.

---

## 6. Aturan berhenti — disepakati SEKARANG

Bot **memeriksa** aturan ini di tiap pesan EXIT dan heartbeat harian, dan
menandainya dengan 🚨. Bot **tidak** menghentikan dirinya sendiri — keputusan
berhenti tetap di tangan Anda.

| Kondisi | Tindakan |
|---|---|
| Drawdown modal kertas menembus **−20%** (−$60 kalau puncaknya $300) | Berhenti, evaluasi ulang |
| **15 kekalahan beruntun** (rekor historis V2: 12) | Berhenti |
| Setelah **100 trade**, expectancy ≤ 0 | Strategi ditolak untuk watchlist ini |
| Ada sinyal live yang **tidak cocok** dengan 8 syarat Report 2.2 | Hentikan sementara, cari sebabnya |
| Kecocokan spot vs perp suatu koin **< 90%** | Pertimbangkan mengeluarkan koin itu — **sebelum** trade pertama |

---

## 7. Yang harus diingat sepanjang forward test

1. **Ini bukan strategi yang terbukti.** Conviction 20%. MA200 adalah hipotesis.
2. **Bandingkan dengan Versi 3, bukan Versi 2.** Acuan jujurnya +0,19 R/trade
   dan win rate ~49%. Angka Versi 2 (+0,26 R) adalah batas atas in-sample.
3. **Tahun pertama bisa flat atau rugi.** Di backtest, 2022 (bear) −10,12 R.
4. **Jangan menambah filter di tengah jalan** (Report 4.2). Satu-satunya yang
   boleh berubah di `config.yaml` tanpa merusak eksperimen: tidak ada.
5. **Tulis kegagalan sejelas keberhasilan.** Forward test yang gagal adalah
   hasil yang valid.
