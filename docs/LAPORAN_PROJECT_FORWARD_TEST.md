# Laporan Project — Forward Test Sequence Snap Versi 2

**Repo:** [`daijobudesu69/Crypto-Sequence-Snap`](https://github.com/daijobudesu69/Crypto-Sequence-Snap) (publik)
**Disusun:** 27 September 2026, status per 04:35 UTC
**Versi mesin saat laporan ditulis:** `snap-v2-fwd-1.3.0`
**Pemilik keputusan:** Dew
**Status forward test:** **BERJALAN** sejak 26 Sep 2026 · paper trading · belum ada trade

> Dokumen ini adalah catatan lengkap bagaimana forward test ini dibangun: apa yang
> diputuskan, kenapa, apa yang diverifikasi, apa yang sempat salah, dan apa yang
> masih tidak diketahui. Ditulis supaya siapa pun yang memegang repo ini enam
> bulan atau dua tahun lagi — termasuk Dew sendiri — bisa merekonstruksi setiap
> keputusan tanpa menurunkannya ulang, dan tahu persis cara membaca hasilnya.
>
> Riset yang mendahului forward test ini ada di dua dokumen terpisah:
> [`Sequence Snap Report Trading Strategy.md`](Sequence%20Snap%20Report%20Trading%20Strategy.md)
> (bukti strategi) dan [`PROJECT_LOG_Sequence-Snap.md`](PROJECT_LOG_Sequence-Snap.md)
> (jejak riset). Laporan ini tidak mengulang isi keduanya kecuali yang perlu.

---

## Daftar isi

| # | Bagian |
|---|---|
| 0 | Ringkasan eksekutif |
| 1 | Latar belakang: kenapa ada forward test |
| 2 | Kronologi keputusan |
| 3 | Strategi yang diuji — aturan persis |
| 4 | Arsitektur sistem |
| 5 | Sumber data dan tracking error |
| 6 | Verifikasi: mesin repo ini = mesin riset |
| 7 | Model eksekusi paper trading |
| 8 | Pencatatan: CSV dan Google Sheets |
| 9 | Telegram: pesan, waktu, dan keterlambatan |
| 10 | Operasional: workflow, secret, jadwal |
| 11 | Cara mengevaluasi hasil dan aturan berhenti |
| 12 | Risiko dan keterbatasan |
| 13 | Yang masih tidak diketahui |
| 14 | Insiden dan perbaikan selama pembangunan |
| 15 | Status saat laporan ditulis |
| 16 | Peta file repo |
| 17 | Perawatan: cara mengubah sesuatu tanpa merusak eksperimen |
| 18 | Penilaian akhir dan conviction |
| L | Lampiran: glosarium, secret, konfigurasi, daftar tes |

---

# 0. Ringkasan eksekutif

**Apa yang dibangun.** Bot di GitHub Actions yang menjalankan strategi Sequence
Snap Versi 2 secara otomatis di **6 koin (ETH, BNB, XRP, DOGE, AVAX, NEAR),
timeframe 4H**, sebagai **paper trading dengan modal kertas $300** dan risiko 1%
($3) per trade. Bot mendeteksi sinyal ~46 detik setelah tiap lilin 4H tutup,
mengirimnya ke **Telegram**, mencatat entry dan exit di atas kertas, menulis
semuanya ke **CSV di repo** dan **Google Sheets**, dan mengirim heartbeat harian.

**Kenapa.** Riset menyimpulkan strategi ini **DITOLAK untuk uang sungguhan
(conviction 20%)**. Versi 1 (pola saja) gagal di data yang belum pernah dilihat
(2021–2023, t = −0,07). Versi 2 (+ filter EMA200) satu-satunya yang bertahan
(t = 1,99) — tapi filter EMA200 sendiri tidak lolos uji formal. Forward test ini
adalah **ujian bersih pertama** Versi 2: data masa depan yang tidak mungkin
pernah dilihat saat riset.

**Apa yang sudah terbukti.**

| Klaim | Bukti |
|---|---|
| Mesin repo = mesin riset | Contoh Report Bagian 3 direplikasi **persis** (RSI 48,52/48,33, stop 2238,88, target 2426,93). Jumlah trade Versi 1 per koin **185 dari 186** sama dengan setup riset. Tes parity langsung terhadap `strategy.py` riset lulus |
| Bot jalan dan cepat | Lilin 20:00, 00:00, 04:00 UTC diproses pada detik ke-**46** setelah tutup |
| Telegram dan Sheets jalan | Workflow tes 27 Sep 04:35 UTC: pesan terkirim; spreadsheet ditulis lalu dibaca balik, semua kolom wajib ada |
| Kode tahan kegagalan | 43 tes otomatis hijau (parity, 8 syarat, mesin posisi, outbox, dedup, feed mundur, state rusak, Sheets mati) |

**Yang harus diingat.**

1. **Ini bukan strategi yang terbukti.** Acuan jujurnya Versi 3 (out-of-sample):
   **+0,19 R per trade, win rate ~49%.** Angka Versi 2 (+0,26 R) adalah batas atas.
2. **Butuh waktu lama.** ~3,5–4 trade per bulan → **100 trade ≈ 2–2,5 tahun.**
3. **Data bot ≠ data backtest.** Backtest memakai Binance futures, yang
   diblokir dari GitHub. Bot memakai Binance spot atau Gate.io perp per koin;
   kecocokan sinyalnya 83–100% tergantung koin.
4. **Aturan berhenti sudah disepakati sebelum trade pertama** (drawdown −20%,
   15 kalah beruntun, expectancy ≤ 0 setelah 100 trade). Bot memeriksa dan
   mengumumkannya; keputusan berhenti tetap di tangan Dew.

---

# 1. Latar belakang: kenapa ada forward test

## 1.1 Hasil riset dalam satu tabel

Dari Report Bagian 5 — tiga "versi" yang sebenarnya dua aturan di dua periode:

| | Versi 1 | Versi 2 | **Versi 3** |
|---|---:|---:|---:|
| Aturan | Pola + RSI | Pola + RSI + **EMA200** | Sama dengan V2 |
| Periode | 2024-01 → 2026-09 | 2024-01 → 2026-09 | **2021-01 → 2023-12** |
| Sifat periode | dipakai membangun | dipakai membangun | **belum pernah dilihat** |
| Trade | 503 | 315 | 168 |
| Expectancy | +0,1855 R | +0,2584 R | **+0,1915 R** |
| t-statistic | 3,34 | 3,67 | **1,99** |
| Max drawdown | 33,52 R | 20,55 R | **11,79 R** |

Dan kolom yang paling menentukan (Report 5.2, 8 koin yang sama):

| | V1 di 2021–23 | **V2 di 2021–23** |
|---|---:|---:|
| Expectancy | **−0,0053 R** | **+0,1915 R** |
| t | **−0,07** | 1,99 |
| Bear market 2022 | −28,48 R | −10,12 R |

Tanpa EMA200, strategi menghasilkan **nol** di data baru. Dengan EMA200 ia masih
positif — tapi (Report 5.4):

- EMA200 **gagal** koreksi multiple testing (p = 0,040 × 5 = **0,200**)
- Penurunan drawdown-nya terbukti artefak jumlah trade (membuang 43% trade secara
  acak memberi drawdown yang justru lebih kecil)
- Memilih EMA200 *karena* ia selamat di OOS = memakai OOS untuk memutuskan

**Kesimpulan riset: EMA200 adalah hipotesis yang belum terbukti. Forward test
inilah ujian ketiganya yang benar-benar bersih.**

## 1.2 Kenapa paper trading, bukan uang sungguhan

Report 10.1: *"Jangan pakai uang sungguhan. Tidak ada satu pun uji yang lolos
bersih."* Forward test dengan uang kertas adalah cara termurah untuk tahu apakah
edge ini nyata. Dew memutuskan **paper trading** sejak awal.

## 1.3 Kenapa Versi 2, bukan Versi 1

Rencana awal (setup V1, 20 Sep 2026) memilih Versi 1 karena return in-sample-nya
lebih tinggi (+21,0% vs +16,1% per tahun di $300). Rencana itu diganti **sebelum
trade pertama** ke Versi 2, karena Versi 1 adalah versi yang gagal di satu-satunya
uji out-of-sample. Setup V1 diarsipkan di
[`arsip/FORWARD_TEST_V1_SETUP.md`](arsip/FORWARD_TEST_V1_SETUP.md), tidak dihapus.

---

# 2. Kronologi keputusan

Semua dalam UTC. Keputusan Dew ditandai **(D)**, keputusan teknis yang saya
ambil dan laporkan ditandai **(T)**.

| Waktu | Keputusan / kejadian | Alasan |
|---|---|---|
| 26 Sep | **(D)** Repo baru `Crypto-Sequence-Snap`, **terpisah total** dari Crypto-MEX | Dua eksperimen tidak boleh berbagi state |
| 26 Sep | **(D)** Isi repo: dokumen, Pine, template log | — |
| 26 Sep | **(D)** Paper trading | Strategi ditolak untuk uang sungguhan |
| 26 Sep | **(D)** Pakai **Versi 2** | V1 gagal OOS |
| 26 Sep | **(D)** Pengiriman Telegram "secepat MEX" | — |
| 26 Sep | **(D)** Opsi A: **bot Python seperti MEX** (bukan alert TradingView) | Satu-satunya opsi yang bisa mengirim Telegram tanpa server sendiri |
| 26 Sep | **(D)** Repo **publik** | Menit Actions publik tidak dibatasi; pemantau nonstop butuh ~43.000 menit/bulan, jauh di atas 2.000 menit gratis repo privat |
| 26 Sep | **(D)** MA200 = **EMA200**; modal **$300** | Sesuai Pine v2 dan Report 6.3 |
| 26 Sep 19:32 | **(T)** Commit pertama; 36 tes hijau | — |
| 26 Sep 19:35 | **(T)** Ukur spot vs perp #1: replikasi Report **COCOK**; ETH/BNB/XRP/DOGE/AVAX 80–93% | — |
| 26 Sep 19:45 | **Forward test dimulai** — 5 koin bootstrap flat di lilin 12:00 UTC | — |
| 26 Sep 20:00:46 | Lilin pertama diproses, 46 detik setelah tutup | Bukti pola "bangun setelah tutup" bekerja |
| 27 Sep 01:42 | **(D)** Cek TRX, XMR, NEAR, TAO; **pakai sumber data yang paling dekat Binance futures per koin** | — |
| 27 Sep 01:45 | **(T)** Ukur 9 koin × 2 sumber; aturan pilih ditetapkan **sebelum** hasil dilihat: kecocokan sinyal | Yang diperdagangkan sinyal, bukan harga |
| 27 Sep 01:48 | **(T)** Watchlist 8 koin; **XMR ditahan** (37,5%) | Tracking data, bukan hasil backtest |
| 27 Sep 02:19 | **(D)** Watchlist final **6 koin**: ETH, BNB, XRP, DOGE, AVAX, **NEAR**; TRX & TAO keluar (66,7%) | — |
| 27 Sep 02:24–02:54 | **(D)** Template sinyal Telegram ditetapkan Dew (ringkas) + satu baris peringatan telat di paling bawah | "Malas membaca terlalu banyak hal" |
| 27 Sep 03:35 | **(T)** Cermin Google Sheets (service account) | Secret Google ditambahkan Dew |
| 27 Sep 03:42 | **(T)** Tab `ringkasan`, sinkron harian, cek baca-balik | Dew: *"pastikan spreadsheet mencatat semua hal yang diperlukan"* |
| 27 Sep 04:00:46 | Lilin 00:00 UTC: 6 koin, 2 sumber data, 46 detik | Verifikasi otomatis terjadwal lulus |
| 27 Sep 04:35 | **Workflow tes: Telegram ✅, Google Sheets ✅** | Semua secret lengkap |

---

# 3. Strategi yang diuji — aturan persis

## 3.1 Pola

Semua dihitung saat lilin 4H **TUTUP** (00, 04, 08, 12, 16, 20 UTC). Penomoran
mundur dari lilin yang baru tutup (bar 0).

```
 bar 5    bar 4    bar 3    bar 2    bar 1    bar 0
[MERAH]  [hijau]  [hijau]  [hijau]  [hijau]  [hijau]  →  ENTRY di OPEN lilin berikutnya
```

| # | Syarat | Rumus persis | Jebakan |
|---|---|---|---|
| 1 | Bar 5 merah | `close[5] < open[5]` | sama dengan = gagal |
| 2 | Bar 0–4 hijau | `close[i] > open[i]`, i = 0..4 | sama dengan = gagal |
| 3 | Tidak turun ke dasar lilin merah | `low[i] > low[5]`, i = 0..4 | **menyentuh sama persis = gagal** |
| 4 | Close naik, toleransi 0,05% | `close[i] > close[i+1] × 0,9995`, **i = 0..3 saja** | `[i+1]` = lilin LEBIH LAMA; pasangan bar 4 vs 5 tidak diperiksa |
| 5 | Momentum | `RSI(14)[0] > 40` | RSI **Wilder/RMA**, bukan EMA |
| 6 | Momentum naik | `RSI(14)[0] > RSI(14)[1]` | — |
| 7 | Posisi kosong di koin itu | — | tidak ada pyramiding |
| **8** | **Tren (Versi 2)** | **`close[0] > EMA200`** | ketat: sama dengan = gagal |

## 3.2 Level dan eksekusi

| Yang dihitung | Rumus | Catatan |
|---|---|---|
| Stop | `low[5]` | beku, **tidak ada trailing** |
| Risiko rencana | `close[0] − low[5]` | dari close bar 0 |
| Target | `close[0] + 1,5 × risiko` | dari close bar 0, beku |
| Entry | **open lilin berikutnya** | = saat bar 0 tutup; market order |
| Qty | `($300 × 1%) ÷ (entry − stop)` | risiko $3 tetap, tidak di-compound |
| Exit | stop atau target, mana yang kena dulu | kena dua-duanya di lilin sama → **stop** (pesimis) |
| Batas waktu | **tidak ada** | rekor backtest V2: 74 hari |

## 3.3 Parameter terkunci (`config.yaml`)

```yaml
paper:
  capital_usd:    300
  risk_pct:       1.0
  commission_pct: 0.05
strategy:
  run_length:       5
  tolerance_pct:    0.05
  rsi_length:       14
  rsi_min_long:     40
  use_rsi_filter:   true
  use_trend_filter: true
  ma_length:        200
  ma_type:          EMA
  take_profit_r:    1.5
```

## 3.4 Yang dilarang (Report 4.2) — dan bagaimana bot menguncinya

| Larangan | Bukti riset | Kunci di bot |
|---|---|---|
| **Sisi short** | 432 trade, t = 0,51 (lempar koin) | Kode hanya menghitung pola bullish; kunci `allow_short` di config **ditolak** saat startup |
| Trailing stop | Drawdown lebih dalam (37,9 R dan 59,4 R vs 33,5 R) | Stop beku di kode |
| Filter tambahan (VixFix, SuperTrend, ADX) | Nol informasi / merugikan | Kunci config asing ditolak |
| Mengubah target 1,5R | Tidak pernah diuji | Terkunci; perubahan wajib dicatat di CHANGELOG |
| Pyramiding | — | Satu posisi per koin |

---

# 4. Arsitektur sistem

## 4.1 Gambaran besar

```
                 GitHub Actions (repo publik, menit tidak dibatasi)
┌──────────────────────────────────────────────────────────────────────────┐
│ signal.yml  — cron "11,41 * * * *" hanya MENYALAKAN pemantau              │
│   └─ pemantau hidup ~5,5 jam, concurrency group snap-state (antre)        │
│        loop:                                                              │
│          refresh_state.sh   tarik state terbaru dari origin               │
│          run_signal.py      proses lilin baru untuk 6 koin                │
│             ├─ datafeed     1.500 bar 4H per koin (sumber per koin)       │
│             ├─ strategy     8 syarat → SIGNAL / ENTRY / EXIT              │
│             ├─ ledger       tulis CSV (+ cermin Sheets)                   │
│             └─ outbox       antre → kirim Telegram → sent_ids             │
│          run_heartbeat.py   1×/hari 07:00 WIB (+ sinkron Sheets)          │
│          save_state.sh      commit state/ (retry, merge berdasarkan isi)  │
│          tidur sampai min(10 menit, lilin 4H berikutnya tutup + 45 dtk)   │
│                                                                           │
│ heartbeat.yml    — cadangan kalau pemantau mati                           │
│ ci.yml           — 43 tes tiap push                                       │
│ measure.yml      — (manual) ukur tracking error + replikasi Report        │
│ test-message.yml — (manual) tes Telegram + tulis & baca balik Sheets      │
└──────────────────────────────────────────────────────────────────────────┘
        │ data                       │ pesan                  │ log
        ▼                            ▼                        ▼
  Binance spot mirror          Telegram (bot baru)     state/*.csv  (resmi)
  Gate.io perp                                          Google Sheets (cermin)
```

## 4.2 Kenapa pemantau panjang, bukan cron biasa

Pelajaran dari Crypto-MEX: cron GitHub **tidak dijamin jalan** — di MEX
keandalannya terukur 23–26% (12 dari ~46 jadwal dalam 26 jam), dengan jeda
terburuk 4 jam 48 menit. Menambah baris cron tidak menolong.

Jadi polanya dibalik: cron hanya **menyalakan** pemantau yang lalu hidup ~5,5 jam
dan mengecek sendiri. Satu cron yang berhasil menutupi 5,5 jam berikutnya; jadwal
yang jatuh saat pemantau masih hidup **antre** di concurrency group dan langsung
mulai begitu yang lama selesai. Jeda pergantian yang terukur di repo ini: ±1 menit.

## 4.3 Beda dari MEX — lebih cepat

MEX mengecek tiap 10 menit, jadi sinyal bisa telat sampai 10 menit. Di sini
pemantau juga **bangun ~45 detik setelah SETIAP lilin 4H tutup**:

```bash
next_close=$(( (now / 14400 + 1) * 14400 + 45 ))
wait = min(600, next_close − now)
```

Terukur: lilin 20:00, 00:00, 04:00 UTC diproses pada **detik ke-46**.

## 4.4 Pengaman yang diwarisi dari MEX (tiap satu lahir dari insiden nyata)

| Pengaman | Masalah yang dicegah |
|---|---|
| **Digerakkan bar, bukan jam** | Run yang telat mengejar bar yang terlewat; bar yang sudah diproses dilewati |
| **Outbox + `sent_ids`** | Kirim gagal dicoba ulang; run yang mati setelah kirim tidak mengirim dua kali |
| **Kunci dedup memuat simbol** | Id sinyal dari waktu bar saja bentrok antar koin (148 dari 439 di backtest MEX) |
| **`last_bar` hanya maju** | Feed cadangan yang tertinggal tidak memutar ulang bar |
| **Commit per bar** | Bar yang meledak tidak membuat bar sebelumnya dicatat dua kali |
| **State rusak = berhenti keras** | File rusak tidak dianggap "run pertama" yang meninggalkan posisi terbuka |
| **Tulis state atomik** | Job yang dibunuh tidak meninggalkan setengah file |
| **`refresh_state.sh`** | Job baru yang checkout sebelum push job lama tidak memproses ulang |
| **`save_state.sh` + `merge_state.py`** | Konflik push diselesaikan berdasarkan ISI (last_bar terbaru per simbol, sent_ids digabung), bukan sisi rebase |
| **`merge=union` untuk CSV** | Dua run yang menambah baris tidak saling membuang |
| **Rotasi header CSV** | Kolom baru tidak menulis di bawah header lama (file jadi tak terbaca) |
| **Pesan exception tanpa isi** | Token bot / kunci Google tidak bocor ke log publik |
| **Satu simbol mati ≠ semua mati** | Feed satu koin yang gagal tidak menghentikan 5 lainnya |

## 4.5 Bootstrap

Run pertama tiap koin **tidak memutar ulang sejarah**: ia mengambil lilin tutup
terbaru dan mulai flat dari sana. Memutar ulang akan menembakkan setumpuk sinyal
basi di hari pertama.

---

# 5. Sumber data dan tracking error

## 5.1 Masalahnya

Backtest memakai arsip **Binance USD-M futures (perp)**. API futures Binance
(`fapi.binance.com`) menjawab **HTTP 451** dari runner GitHub (IP AS diblokir).
Dua pengganti yang bisa dijangkau:

| Sumber | Pasar | Bursa | Sifat |
|---|---|---|---|
| `data-api.binance.vision` | **Spot** | Binance (sama) | Order book berbeda dari futures |
| `api.gateio.ws` | **Perp** (sama jenisnya) | Gate.io (berbeda) | Harga dari bursa lain |

Selisih harga ±0,05% terdengar kecil, tapi aturan Sequence Snap tajam persis di
ukuran itu: toleransi close 0,05%, `low` sama persis = gagal, `close > EMA200`
ketat, `RSI > 40`. Selisih kecil bisa membalik sinyal.

## 5.2 Cara mengukur

`tools/measure_spot_vs_perp.py` (workflow "Ukur spot vs perp"):

1. Unduh arsip resmi `data.binance.vision` — futures dan spot — Jan 2024 s/d
   Ags 2026, plus riwayat Gate.io perp lewat API berhalaman.
2. Jalankan **mesin forward test yang sama** di tiap seri.
3. Bandingkan sinyal Versi 2 bar demi bar sejak 1 Jul 2024 (6 bulan pemanasan
   EMA200) atau 1.000 bar setelah data sumber mulai.

**Kecocokan** = sinyal cocok ÷ (sinyal futures + sinyal palsu). Sinyal yang
hilang **dan** sinyal yang tidak pernah ada di backtest sama-sama dihitung meleset.

**Aturan pilih — ditetapkan sebelum hasil dilihat:**
1. Kecocokan sinyal tertinggi
2. Seri (< 1 poin persen) → beda harga close 90 hari terakhir terkecil
3. Sumber tanpa data koin itu gugur

## 5.3 Hasil lengkap (diukur 27 Sep 2026)

| Koin | Sumber | Beda close | Beda close 90 hr | Beda high/low | Sinyal futures | Cocok | Hilang | Palsu | **Kecocokan** | ΣR sumber | ΣR futures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ETH | **Binance spot** ✅ | 0,046% | 0,047% | 0,046% | 23 | 21 | 2 | 1 | **87,5%** | +13,46 | +14,94 |
| ETH | Gate perp | 0,009% | 0,006% | 0,015% | 23 | 19 | 4 | 2 | 76,0% | +12,01 | |
| BNB | **Binance spot** ✅ | 0,046% | 0,056% | 0,047% | 28 | 24 | 4 | 1 | **82,8%** | +5,16 | +11,95 |
| BNB | Gate perp | 0,072% | 0,109% | 0,071% | 28 | 23 | 5 | 4 | 71,9% | +8,13 | |
| XRP | **Binance spot** ✅ | 0,051% | 0,053% | 0,052% | 20 | 18 | 2 | 0 | **90,0%** | +9,19 | +9,67 |
| XRP | Gate perp | 0,012% | 0,009% | 0,017% | 20 | 18 | 2 | 1 | 85,7% | +8,16 | |
| DOGE | Binance spot | 0,049% | 0,055% | 0,050% | 14 | 13 | 1 | 0 | 92,9% | +6,84 | +5,83 |
| DOGE | **Gate perp** ✅ | 0,014% | 0,014% | 0,018% | 14 | 14 | 0 | 0 | **100%** | +5,83 | |
| AVAX | Binance spot | 0,056% | 0,062% | 0,058% | 10 | 8 | 2 | 2 | 66,7% | +4,86 | +2,38 |
| AVAX | **Gate perp** ✅ | 0,031% | 0,015% | 0,030% | 10 | 9 | 1 | 0 | **90,0%** | +0,91 | |
| NEAR | Binance spot | 0,064% | 0,061% | 0,066% | 14 | 12 | 2 | 0 | 85,7% | +5,35 | +4,35 |
| NEAR | **Gate perp** ✅ | 0,042% | 0,031% | 0,043% | 14 | 13 | 1 | 0 | **92,9%** | +2,91 | |
| TRX | Binance spot | 0,054% | 0,061% | 0,056% | 39 | 25 | 14 | 5 | 56,8% | +6,44 | +6,76 |
| TRX | Gate perp | 0,025% | 0,021% | 0,025% | 39 | 30 | 9 | 6 | 66,7% | −0,09 | |
| TAO | Binance spot | 0,053% | 0,061% | 0,057% | 11 | 5 | 6 | 2 | 38,5% | +6,43 | +7,33 |
| TAO | Gate perp | 0,039% | 0,037% | 0,042% | 11 | 8 | 3 | 1 | 66,7% | +6,79 | |
| XMR | Binance spot | — | — | — | 21 | 0 | 21 | 0 | 0% | — | +2,07 |
| XMR | Gate perp | 0,141% | 0,048% | 0,134% | 21 | 9 | 12 | 3 | 37,5% | +6,21 | |

✅ = sumber utama yang dipakai bot. Sumber lainnya jadi **cadangan otomatis**.

## 5.4 Keputusan

| Koin | Sumber utama | Kecocokan | Keputusan |
|---|---|---:|---|
| ETH | Binance spot | 87,5% | **Dipakai** |
| BNB | Binance spot | 82,8% | **Dipakai** (tracking paling lemah di antara yang dipakai) |
| XRP | Binance spot | 90,0% | **Dipakai** |
| DOGE | Gate perp | 100% | **Dipakai** |
| AVAX | Gate perp | 90,0% | **Dipakai** |
| NEAR | Gate perp | 92,9% | **Dipakai** (ditambahkan 27 Sep) |
| TRX | Gate perp | 66,7% | **Tidak dipakai** — 1 dari 3 sinyal berbeda |
| TAO | Gate perp | 66,7% | **Tidak dipakai** — 1 dari 3 sinyal berbeda |
| XMR | Gate perp | 37,5% | **Tidak dipakai** — lebih dari separuh berbeda; spot Binance sudah delisting |

**Semua pengeluaran koin berdasarkan tracking data, BUKAN hasil backtestnya.**
Memilih koin karena backtestnya bagus adalah data snooping.

## 5.5 Tiga pelajaran dari pengukuran

1. **Harga terdekat ≠ sinyal terdekat.** Di ETH, harga Gate **5× lebih dekat**
   (0,009% vs 0,046%) tapi sinyalnya lebih jauh (76% vs 87,5%). Sama di XRP.
   Penyebabnya **tidak saya ketahui** — dugaan: aturan "low sama persis" dan
   "lilin hijau/merah" peka terhadap tick terakhir, bukan rata-rata harga.
2. **ΣR adalah ukuran paling berisik.** Dengan 10–40 trade per koin, satu trade
   yang berubah dari −1 ke +1,5 menggeser 2,5 R. Contoh ekstrem: TRX Gate lebih
   cocok sinyalnya (66,7% vs 56,8%) tapi ΣR-nya −0,09 vs +6,76 futures.
   Karena itu ΣR **tidak** dipakai untuk memilih.
3. **Sampel kecil.** AVAX cuma 10 sinyal; 1 sinyal = 10 poin persen. Semua
   angka kecocokan di atas punya ketidakpastian lebar.

## 5.6 Kenapa 1.500 bar, bukan 1.000

EMA200 punya ekor panjang: sisa pengaruh nilai awal setelah k bar adalah
(1 − 2/201)^k. Di 1.000 bar masih ~0,005%, di 1.500 bar ~0,00003%. Syarat #8
membandingkan close dengan EMA200 secara ketat, jadi di dekat persilangan selisih
sekecil itu pun bisa membalik sinyal. Binance membatasi 1.000 bar per
permintaan, jadi diambil dua halaman; Gate diambil per halaman 1.000 bar lewat
rentang waktu (Gate menolak `limit` bersama `from`/`to`).

## 5.7 Pengaman data

`sanity_check()` menolak seri yang: < 1.000 bar, punya bar duplikat, punya bar
hilang, basi (> 12 jam), OHLC cacat (high < low dsb.), atau berisi NaN/inf. Seri
yang ditolak membuat bot mencoba sumber cadangan; kalau keduanya gagal, koin itu
dilewati di run itu dan dicatat `partial_data`.

---

# 6. Verifikasi: mesin repo ini = mesin riset

Ini bagian terpenting sebelum forward test boleh dimulai. Kalau mesinnya berbeda,
18 bulan forward test menguji strategi lain dari yang dibacktest.

## 6.1 Replikasi contoh Report Bagian 3 (data Binance futures asli)

| | Report | Repo ini |
|---|---:|---:|
| Sinyal ETHUSDT 2024-09-09 08:00 UTC (Versi 1) | ada | **ada** |
| RSI bar 0 | 48,52 | **48,52** |
| RSI bar 1 | 48,33 | **48,33** |
| Stop | 2238,88 | **2238,88** |
| Target | 2426,93 | **2426,93** |
| close vs EMA200 | — | −10,63% → **diblokir** filter V2 |

**COCOK.** RSI dua desimal identik membuktikan smoothing Wilder/RMA benar.

## 6.2 Jumlah trade Versi 1, 2024-01..2026-08 (futures)

| Koin | Repo ini | Setup V1 (s/d 19 Sep 2026) |
|---|---:|---:|
| ETH | 43 | 43 |
| BNB | 41 | 42 |
| XRP | 39 | 39 |
| DOGE | 37 | 37 |
| AVAX | 25 | 25 |
| **Total** | **185** | **186** |

Satu trade BNB selisih karena September 2026 tidak ikut di arsip bulanan.

## 6.3 Parity langsung dengan kode riset

`tests/reference/research_strategy.py` adalah `strategy.py` riset **apa adanya**.
Tes `test_parity_dengan_kode_riset` menjalankan keduanya di 6 seri acak × 1.500
bar dan menuntut array sinyal **identik**:

- Versi 1: `setup_repo == setup_riset`
- Versi 2: `setup_repo == setup_riset AND close > EMA200`
- Stop tiap sinyal = `low[5]` yang sama

## 6.4 Batas-batas syarat (Report 2.2 "tiga jebakan")

| Tes | Yang dibuktikan |
|---|---|
| `test_syarat1_lilin_merah_ketat` | close == open bukan lilin merah |
| `test_syarat3_low_sama_persis_gagal` | low == low[5] membatalkan |
| `test_syarat4_batas_toleransi_persis_gagal` | close tepat di batas 0,9995 gagal; +0,01 lolos |
| `test_syarat4_hanya_empat_pasang` | bar 4 boleh tutup di bawah bar 5 |
| `test_syarat8_ema200_ketat` | close == EMA200 diblokir |
| `test_rsi_pakai_rma_bukan_ema` | RSI = rekursi Wilder persis |
| `test_hasil_trade_contoh_report` | entry 2314,09 → target → **R = +1,468** (Report: +1,468) |

## 6.5 Total

**43 tes otomatis**, semuanya hijau, dijalankan CI di setiap push. Daftar lengkap
di Lampiran L4.

---

# 7. Model eksekusi paper trading

## 7.1 Alur per lilin (`snap/strategy.py` → `step()`)

```
A. Ada sinyal dari lilin sebelumnya?  → ENTRY di OPEN lilin ini
B. Ada posisi (termasuk yang baru masuk)? → uji stop & target di lilin ini
      open ≤ stop            → keluar di OPEN (gap)          alasan: stop
      open ≥ target          → keluar di OPEN (gap)          alasan: target
      low ≤ stop             → keluar di STOP                 (duluan, pesimis)
      high ≥ target          → keluar di TARGET
C. Posisi kosong dan pola terbentuk di CLOSE lilin ini? → SIGNAL
```

Posisi yang keluar di lilin ini sudah flat saat close, jadi lilin yang sama boleh
menghasilkan sinyal baru — sama seperti Pine.

## 7.2 Satuan hasil

| Ukuran | Rumus |
|---|---|
| R kotor | `(exit − entry) ÷ (entry − stop)` |
| R bersih (`R_realisasi`) | R kotor − komisi dua sisi dalam R |
| Komisi dalam R | `0,05% × (entry + exit) ÷ (entry − stop)` |
| PnL paper | `qty × (exit − entry) − qty × 0,05% × (entry + exit)` |
| Qty | `$3 ÷ (entry − stop)` |

Risiko $3 dihitung dari **modal awal** $300, tidak di-compound (PROJECT_LOG D4),
supaya R bisa dijumlahkan linear.

## 7.3 Yang TIDAK dimodelkan

| Tidak dimodelkan | Kenapa | Dampak yang diketahui |
|---|---|---|
| **Funding** | API funding Binance futures juga diblokir dari runner | Report: rata-rata +0,012 R/trade (~6% expectancy); 13,8% trade justru menerima |
| **Slippage** | Paper fill di open / di level persis | Backtest asumsi 1 tick; bisa lebih buruk di koin tipis |
| **MIN_NOTIONAL penolakan** | Dicatat (`dilewati_min_notional`), tidak ditolak | Di $300 hampir semua sinyal lolos (Report 6.3) |
| **Margin / leverage tier / likuidasi** | — | Posisi terlama backtest V2: 74 hari |

Kolom `slippage_entry_tick`, `slippage_exit_tick`, `funding_dibayar_usd`
sengaja dibiarkan kosong di `trades` — hanya bisa diisi dari eksekusi sungguhan.

---

# 8. Pencatatan: CSV dan Google Sheets

## 8.1 Prinsip

**CSV di repo adalah catatan resmi.** Google Sheets hanya cermin. Gagal menulis
ke Sheets tidak pernah menggagalkan run, dan status cermin dicatat per run.

## 8.2 File di `state/`

| File | Isi | Kapan bertambah |
|---|---|---|
| `trades.csv` | 1 baris per trade selesai | Saat EXIT |
| `events.csv` | 1 baris per SIGNAL / ENTRY / EXIT | Saat kejadian |
| `runs.csv` | Bukti hidup: waktu, status, sumber data, Telegram, Sheets | Tiap run yang memproses bar / gagal; run kosong maks 1×/jam |
| `runs.v1.csv` | Arsip `runs.csv` sebelum kolom `sheet` ditambahkan | — |
| `position.json` | State mesin per koin, outbox, sent_ids, tanggal heartbeat | Tiap perubahan |

## 8.3 Kolom `trades` (= `forward_test_log.csv` + provenance)

| Kolom | Isi |
|---|---|
| `no` | nomor urut |
| `koin` | ETHUSDT … NEARUSDT |
| `waktu_sinyal_utc` | open time lilin sinyal (bar 0) |
| `waktu_entry_utc` | open time lilin entry |
| `close_bar0` | close lilin sinyal |
| `low_bar5` | low lilin merah = stop |
| `rsi_bar0`, `rsi_bar1` | verifikasi syarat 5–6 |
| `ema200_bar0` | verifikasi syarat 8 |
| `stop_rencana`, `target_rencana` | level beku |
| `harga_entry_aktual` | paper: open lilin entry |
| `qty`, `notional` | ukuran posisi paper |
| `dilewati_min_notional` | TRUE bila notional < minimum Binance (ETH $20, lainnya $5 — asumsi) |
| `harga_exit_aktual`, `alasan_exit`, `waktu_exit_utc`, `bar_ditahan` | hasil |
| `slippage_entry_tick`, `slippage_exit_tick`, `funding_dibayar_usd` | **kosong** — isi manual bila eksekusi sungguhan |
| `pnl_usd`, `R_realisasi` | hasil bersih komisi |
| `catatan` | "paper: fill = open/level, tanpa slippage & funding" |
| `signal_id`, `data_source`, `engine_version` | provenance |
| `R_kotor`, `entry_vs_close_bar0_pct`, `mae_pct`, `mfe_pct`, `notified` | analisis |

## 8.4 Kolom `events` (34)

Identitas (`logged_at_utc`, `event`, `signal_id`, `symbol`, `bar_time_utc`,
`data_source`, `engine_version`, `run_id`, `commit_sha`), latensi
(`signal_to_send_minutes`, `send_status`), level (`signal_close`, `stop`,
`target`, `risk_pct_of_price`), hasil (`entry_price`, `qty`, `notional_usd`,
`exit_price`, `exit_reason`, `bars_held`, `R_gross`, `R_net`, `pnl_usd`), dan
snapshot lilin (`open`, `high`, `low`, `close`, `volume`, `rsi_bar0`, `rsi_bar1`,
`ema200_bar0`, `close_vs_ema200_pct`, `low_bar5`).

`send_status = EXPIRED_BEFORE_SEND` menandai sinyal yang terlambat terlalu lama
untuk dikirim — **tetap dicatat** supaya forward test lengkap.

## 8.5 Google Sheets

Spreadsheet: "Crypto-Sequence" (milik Dew), dibagikan ke service account
`crypto-sequence-snap@crypto-sequence-snap.iam.gserviceaccount.com` (Editor).

| Tab | Isi | Diperbarui |
|---|---|---|
| `events` | cermin `events.csv` | tiap kejadian + sinkron harian |
| `trades` | cermin `trades.csv` | tiap trade + sinkron harian |
| `runs` | cermin `runs.csv` (termasuk arsip) | tiap run tercatat + sinkron harian |
| `ringkasan` | ditulis ulang utuh | tiap trade selesai + harian 07:00 WIB |

Isi tab `ringkasan`:

- **Setup:** mulai, watchlist, timeframe, modal, risiko, komisi, yang tidak dimodelkan
- **Progres:** sinyal tercatat, trade selesai, progres x/100, posisi terbuka
- **Hasil vs acuan:** expectancy & win rate di samping acuan V3 (0,1915 / 49,4%) dan V2 (0,2584 / 51,7%); total R, PnL, equity
- **Risiko vs batas:** drawdown sekarang & terdalam (batas −20%), kalah beruntun sekarang & terpanjang (batas 15), expectancy setelah 100 trade; status tiap aturan
- **Per koin:** sumber data, trade, win, total R, expectancy, posisi terbuka, tanggal mulai

**Sinkron harian** membaca seluruh riwayat CSV (termasuk arsip rotasi header) dan
menambahkan baris yang belum ada di Sheets — baris yang dulu gagal dicerminkan
terisi sendiri.

**Verifikasi 27 Sep 04:35 UTC:** `tools/sheets_check.py` menulis, membaca balik,
dan memastikan: `trades` memuat semua kolom `forward_test_log.csv`; `events`
memuat RSI/EMA200/stop/target; `runs` memuat status Telegram dan Sheets; jumlah
baris Sheets ≥ jumlah baris CSV. Hasil: **SEMUA OK**.

---

# 9. Telegram: pesan, waktu, dan keterlambatan

Bot Telegram **terpisah dari MEX**. Pesan dikirim **hanya kalau ada kejadian**;
berhari-hari sunyi itu normal.

## 9.1 Sinyal — template ditetapkan Dew

```
🟢 SEQUENCE SNAP v2 — LONG · ETHUSDT
Timeframe 4H · lilin sinyal 27-09-2026 15:00–19:00 WIB sudah tutup

🎯 ENTRY: SEKARANG, market order
Lilin 4H berikutnya buka 27-09-2026 19:00 WIB
Harga acuan: 2,314.10 (close lilin sinyal ≈ open lilin berikutnya)

🛑 Stop: 2,238.88 (-3.25% dari acuan, low lilin merah)
✅ Target: 2,426.93 (+4.88% dari acuan, 1.5R)
Dua angka ini MATI: tidak ikut harga entry Anda, tidak ada trailing,
posisi ditahan sampai salah satunya kena.

📐 Ukuran posisi (paper $300, risiko 1.0% = $3.00)
di harga acuan: 0.039883 ETH · notional $92.29
harga entry beda? qty = 3.00 ÷ (harga entry − 2,238.88)
```

Hanya kalau terlambat, satu baris ditambahkan **paling bawah**:

```
⚠️ Terlambat 32 menit — cek harga masih di antara stop dan target.
⚠️ Tertahan 12 menit di antrean kirim — cek harga masih di antara stop dan target.
```

## 9.2 Pesan lain

| Pesan | Kapan tiba | Isi |
|---|---|---|
| 📌 ENTRY TERCATAT (paper) | saat lilin entry **TUTUP** — ±4 jam setelah sinyal | harga entry, selisih vs close sinyal, stop, target, jarak risiko, qty |
| ✅ / 🛑 EXIT | saat lilin tempat stop/target kena **TUTUP** — 0–4 jam setelah harga menyentuh level | R bersih & kotor, $ paper, lama tahan, MAE/MFE, total, kalah beruntun, drawdown; blok 🚨 bila aturan berhenti terpicu |
| 💓 hidup | 1×/hari 07:00 WIB | lilin terakhir, sumber data, posisi per koin + R belum terealisasi, 30 hari, total, progres x/100, drawdown, kalah beruntun |
| ⚠️ alert | semua feed mati / state rusak | detail error (tanpa secret) |

**Penting — ENTRY dan EXIT adalah catatan, bukan instruksi.** Bot hanya membaca
lilin yang sudah tutup (tidak ada data intrabar), jadi ia baru tahu harga open
lilin entry, atau bahwa stop/target tersentuh, setelah lilin itu tutup. Satu-satunya
pesan yang harus ditindaklanjuti segera adalah **SINYAL**. Kalau Dew mengeksekusi
manual, stop dan target dipasang di exchange saat entry, sehingga exit terjadi di
exchange tanpa menunggu pesan bot.

## 9.3 Waktu entry — penjelasan untuk pembaca pesan

Entry di **lilin 4H berikutnya**, yang buka **tepat saat lilin sinyal tutup**.
Pesan datang ±46 detik setelahnya → entry = **sekarang**. Backtest masuk di
**open lilin itu**, satu angka persis (bukan range); open hampir selalu sama
dengan close lilin sinyal (median selisih 0,01%).

## 9.4 Kalau pesan terlambat

| Keterlambatan | Bot (paper) | Pesan | Yang sebaiknya dilakukan |
|---|---|---|---|
| < 15 menit | entry di open, persis | normal | market order, catat fill |
| 15 menit – 4 jam | entry di open, persis | + ⚠️ "Terlambat X menit" | masuk hanya bila harga masih di antara stop dan target |
| > 4 jam (lilin entry sudah tutup) | entry di open, persis | **tidak dikirim** (`EXPIRED_BEFORE_SEND`) | — |

Risiko dalam dolar tetap $3 karena qty dihitung dari entry Anda; yang berubah
adalah **potensi untung** karena target beku. Contoh ETH:

| Harga saat Anda masuk | Untung bila target kena |
|---|---:|
| −0,3% dari acuan | +1,75 R |
| acuan | **+1,50 R** |
| +0,3% | +1,29 R |
| +1,0% | +0,91 R |

Kira-kira: **R yang hilang ≈ % harga bergeser ÷ % risiko.**

---

# 10. Operasional: workflow, secret, jadwal

## 10.1 Workflow

| Workflow | Pemicu | Tugas |
|---|---|---|
| **Sequence Snap signal** (`signal.yml`) | cron `11,41 * * * *` + manual | Pemantau 5,5 jam: sinyal, heartbeat, simpan state |
| **Sequence Snap heartbeat** (`heartbeat.yml`) | cron `27 1,5,9 * * *` + manual (opsi `force`) | Cadangan heartbeat saat pemantau mati |
| **tests** (`ci.yml`) | push ke main, PR, manual | 43 tes offline |
| **Ukur spot vs perp** (`measure.yml`) | manual | Replikasi Report + tracking error 9 koin → `docs/SPOT_VS_PERP.md` |
| **Kirim pesan tes** (`test-message.yml`) | manual | Tes Telegram + tulis & baca-balik Sheets |

## 10.2 Secret (Settings → Secrets and variables → Actions)

| Secret | Isi | Status |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | token bot (dari @BotFather) — **bot khusus repo ini** | ✅ |
| `TELEGRAM_CHAT_ID` | angka chat id saja (grup diawali `-`) | ✅ |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | isi file kunci JSON service account | ✅ |
| `GSHEET_SPREADSHEET_ID` | ID dari URL spreadsheet (antara `/d/` dan `/edit`) | ✅ |

Telegram butuh dua-duanya; Sheets juga. Bila setengah terisi, bot mencetak
petunjuk yang menyebut apa yang kurang.

## 10.3 Jadwal waktu (WIB = UTC+7)

| Kejadian | UTC | WIB |
|---|---|---|
| Lilin 4H tutup | 00, 04, 08, 12, 16, 20 | 07, 11, 15, 19, 23, 03 |
| Bot memproses | +±46 detik | +±46 detik |
| Heartbeat | 00:00–00:10 | 07:00–07:10 |
| Cadangan heartbeat | 01:27, 05:27, 09:27 (hanya bila belum terkirim) | 08:27, 12:27, 16:27 |

## 10.4 Yang perlu dicek Dew

| Kapan | Cek |
|---|---|
| Sekali | Notifikasi email GitHub untuk workflow gagal (Settings akun → Notifications → Actions → *Only notify for failed workflows*) |
| Sinyal pertama | Cocokkan di TradingView (`pine/SequenceSnap_v2.pine`, chart futures mis. `BINANCE:ETHUSDT.P`): panah muncul di lilin yang sama? Kalau beda → hentikan dulu, cari sebab (setup §6). Untuk DOGE/AVAX/NEAR (data Gate) selisih kecil wajar |
| Tiap hari | Heartbeat 07:00 WIB datang. Tidak datang = bot kemungkinan mati → cek tab Actions |
| Tiap 20–25 trade (~6 bulan) | Bandingkan dengan acuan **Versi 3** (+0,19 R, WR ~49%), bukan V2 |
| Tiap ~3 bulan | Jalankan ulang "Ukur spot vs perp" — tracking masih sama? |

---

# 11. Cara mengevaluasi hasil dan aturan berhenti

## 11.1 Acuan

| Acuan | Expectancy | Win rate | Max DD | Kalah beruntun | Sifat |
|---|---:|---:|---:|---:|---|
| **Versi 3** | **+0,1915 R** | **49,4%** | 11,79 R | 7 | **out-of-sample — acuan jujur** |
| Versi 2 | +0,2584 R | 51,7% | 20,55 R | 12 | in-sample — batas atas optimis |
| $300 setelah 1 tahun (V3) | $332,06 (+10,7%) | | | | Report 6.3, 15 koin |
| $300 setelah 1 tahun (V2) | $390,32 (+30,1%) | | | | Report 6.3, 15 koin |

Versi 2 di Binance futures **per koin watchlist** (Jul 2024 – Ags 2026,
in-sample, **bukan validasi**):

| Koin | Trade | Trade/bulan | Win rate | Expectancy | ΣR |
|---|---:|---:|---:|---:|---:|
| ETH | 22 | 0,85 | 68% | +0,679 R | +14,94 |
| BNB | 27 | 1,04 | 59% | +0,443 R | +11,95 |
| XRP | 20 | 0,77 | 60% | +0,484 R | +9,67 |
| DOGE | 14 | 0,54 | 57% | +0,416 R | +5,83 |
| AVAX | 10 | 0,38 | 50% | +0,238 R | +2,38 |
| NEAR | 13 | 0,50 | 54% | +0,335 R | +4,35 |
| **Total 6 koin** | **106** | **~4,1** | | | |

Angka per koin ini jauh di atas acuan V3 — **itu yang diharapkan dari data
in-sample** dan bukan ekspektasi. Tahun pertama bisa flat atau rugi (di backtest,
2022 bear: −10,12 R).

## 11.2 Frekuensi dan durasi

| Sumber | Trade/bulan, 6 koin | 100 trade dalam |
|---|---:|---:|
| V2 per koin, in-sample | ~4,1 | ~24 bulan |
| V3 (0,59/koin), out-of-sample | ~3,5 | ~28 bulan |

**~1 trade tiap 7–9 hari. 100 trade ≈ 2–2,5 tahun.** Di bear market (harga di
bawah EMA200) bisa **berminggu-minggu tanpa sinyal** — itu perilaku yang
diharapkan, bukan bot rusak.

Breadth efektif antar koin hanya ~1,5 (Report 7.2: korelasi return harian
rata-rata 0,62) — 6 koin tidak berarti 6× informasi, dan mereka cenderung rugi
berbarengan.

## 11.3 Aturan berhenti (disepakati sebelum trade pertama)

| Kondisi | Tindakan | Diperiksa bot? |
|---|---|---|
| Drawdown modal kertas menembus **−20%** (dari puncak) | Berhenti, evaluasi ulang | ✅ EXIT + heartbeat + ringkasan |
| **15 kekalahan beruntun** (rekor historis V2: 12) | Berhenti | ✅ |
| Setelah **100 trade**, expectancy ≤ 0 | Strategi ditolak untuk watchlist ini | ✅ |
| Sinyal live **tidak cocok** dengan 8 syarat | Hentikan sementara, cari sebab | ❌ manual (TradingView) |
| Slippage nyata > 3× asumsi (bila eksekusi manual) | Hitung ulang proyeksi | ❌ manual |

Bot **menandai** dengan 🚨 tapi **tidak menghentikan dirinya sendiri** —
forward test yang berhenti diam-diam tidak bisa dibedakan dari yang rusak.

## 11.4 Cara membaca hasil (kerangka keputusan)

| Setelah ~100 trade | Tafsiran |
|---|---|
| Expectancy ≥ +0,15 R, drawdown < 15 R | Konsisten dengan V3. EMA200 selamat ujian ketiga. Baru layak didiskusikan uang kecil |
| 0 < expectancy < +0,15 R | Tidak bisa dibedakan dari nol dengan 100 trade (SE ≈ 0,12 R). Lanjut atau tolak — bukan uang |
| Expectancy ≤ 0 | Ditolak. Hasil yang valid dan berharga |

Standard error expectancy dengan 100 trade di strategi 2-titik (−1 / +1,5 R)
sekitar **0,12–0,13 R** — jadi bahkan +0,19 R hanya ~1,5 SE dari nol. 100 trade adalah
**ambang minimum**, bukan bukti.

## 11.5 Yang TIDAK boleh dilakukan selama forward test

- Menambah filter karena "kelihatannya membantu" (Report 4.2)
- Mengubah target, stop, atau parameter apa pun tanpa CHANGELOG
- Mengeluarkan koin karena hasil forward test-nya jelek (itu data snooping —
  kecuali tracking datanya rusak, yang bukan soal hasil)
- Menyalakan short

---

# 12. Risiko dan keterbatasan

| Risiko | Arah dampak | Mitigasi |
|---|---|---|
| **Tracking error sumber data** (83–100% kecocokan sinyal) | Forward test menguji seri yang sedikit berbeda dari backtest | Sumber dipilih per koin; `data_source` di tiap baris; bisa dipisah saat evaluasi |
| **Funding tidak dimodelkan** | Hasil ~6% terlalu optimis rata-rata; bisa jauh lebih buruk di puncak euforia (saat strategi long paling aktif) | Dicatat sebagai keterbatasan; Report: +0,012 R/trade |
| **Slippage tidak dimodelkan** | Optimis, terutama saat stop tereksekusi di pasar cepat | Kolom slippage untuk eksekusi manual |
| **Cron GitHub tidak andal** | Jeda pemantau → sinyal telat | Pemantau 5,5 jam + antrean; peringatan telat di pesan; sinyal tetap dicatat |
| **GitHub mematikan jadwal repo publik yang 60 hari tanpa aktivitas** | Bot berhenti | Bot commit tiap jam (saya cukup yakin dihitung aktivitas, tidak 100%); heartbeat yang berhenti = alarm |
| **API Binance/Gate berubah atau memblokir** | Data hilang | Dua sumber saling cadangan; heartbeat menampilkan "data tidak terjangkau" |
| **Korelasi antar koin** (breadth ~1,5) | Kerugian berbarengan; p-value lebih lemah dari kelihatannya | Evaluasi di tingkat portofolio, bukan per koin |
| **Sampel kecil per koin** | Hasil per koin tidak bermakna | Evaluasi gabungan; jangan buang koin per hasil |
| **Posisi sangat lama** (rekor V2 74 hari) | Modal kertas terikat; bot harus tetap hidup | Tidak ada batas waktu sesuai riset |
| **Node.js 20 deprecation** (warning di Actions) | Suatu hari `actions/checkout@v4` / `setup-python@v5` bisa berhenti | Naikkan versi action lewat PR saat GitHub mewajibkan |

---

# 13. Yang masih tidak diketahui

1. **Apakah EMA200 bertahan di periode ketiga.** Itulah pertanyaan forward test ini.
2. **Kenapa harga terdekat tidak memberi sinyal terdekat** (ETH, XRP di Gate).
3. **Seberapa jauh harga bergerak 10 menit setelah pola ini muncul** — belum pernah diukur; menentukan biaya pesan yang telat.
4. **Apakah TRX, NEAR, TAO bagian dari universe 15 koin riset.** Daftar 15 koin tidak ada di dokumen yang tersedia. NEAR dipakai tanpa kepastian ini.
5. **Nilai MIN_NOTIONAL dan tickSize terkini** — berstatus asumsi (snapshot 7 Sep 2026).
6. **Funding di rezim ekstrem** — 2024–2026 funding-nya jinak.
7. **Apakah commit bot dihitung "aktivitas" oleh GitHub** untuk aturan 60 hari.
8. **Kenapa BTC terburuk out-of-sample** di riset (tidak relevan langsung — BTC tidak di watchlist — tapi masih terbuka).

---

# 14. Insiden dan perbaikan selama pembangunan

Semua ditemukan **sebelum** trade pertama. Tidak ada yang menyentuh aturan strategi.

| # | Insiden | Cara ketahuan | Perbaikan |
|---|---|---|---|
| F1 | Membuat repo lewat API ditolak (HTTP 403) — integrasi GitHub tidak boleh membuat repo | Error saat `create_repository` | Dew membuat repo manual; Claude GitHub App dipasang |
| F2 | File riset ada di disk laptop (`C:\…`) yang tidak terjangkau dari cloud | — | Dew mengunggah Pine v2, Report, `strategy.py`, template log |
| F3 | Container pengembangan tidak bisa menjangkau Binance/Gate (proxy 403) | Probe koneksi | Pengukuran dipindah ke GitHub Actions (`measure.yml`) |
| F4 | Parser arsip crash: `pd.Timestamp` menolak `numpy.str_` | Smoke test offline | Konversi mikrodetik → milidetik divektorisasi |
| F5 | YAML heartbeat tidak valid (`: ` di perintah satu baris) | Validasi YAML | Pakai blok `run: |` |
| F6 | Tes parity gagal memuat modul riset (dataclass butuh modul terdaftar) | Tes merah | Daftarkan di `sys.modules` |
| F7 | Harapan tes R salah (komisi 0,14 R di data sintetis) | Tes merah | Tes diubah: R kotor tepat 1,5; R bersih < 1,5 |
| F8 | `$+4.40` tampil salah | Render pesan | Helper `usd()` → `+$4.40` |
| F9 | Jam di EXIT/heartbeat = jam BUKA lilin tanpa label, sinyal = jam TUTUP | Render semua template | EXIT menampilkan rentang lilin; heartbeat jam tutup |
| F10 | "Entry: market di OPEN lilin berikutnya" ambigu (lilin apa? kapan? range?) | Pertanyaan Dew | Template diperjelas, lalu diringkas sesuai template Dew |
| F11 | Klaim "TRX/NEAR/TAO tidak ada di universe riset" tidak berdasar | Tinjauan sendiri | Dikoreksi: "belum dipastikan" |
| F12 | Salah tafsir Dew bahwa NEAR "lemah" — sebenarnya 92,9% | Pertanyaan Dew | Diklarifikasi; yang lemah TRX & TAO |
| F13 | Kolom `sheet` tidak masuk header `runs.csv` (penggantian teks meleset) | Tes merah | Diperbaiki langsung |
| F14 | **Sinkron Sheets akan melewatkan baris baru setelah rotasi header** (hanya menghitung file aktif) | Tinjauan sebelum push | `read_history()` membaca arsip + file aktif |
| F15 | Tes Sheets memanggil jaringan sungguhan lewat `reachable()` → crash `cryptography` di container | Tes merah (lokal saja) | Semua jalur jaringan Sheets dipalsukan di tes |
| F16 | Cron pertama tidak jalan dalam ~10 menit setelah repo dibuat | Daftar run kosong | Pemantau dinyalakan manual (mode loop) |
| F17 | Penjelasan ke Dew bahwa pesan ENTRY "dikirim bersamaan dengan sinyal" — keliru; ENTRY tiba saat lilin entry tutup (±4 jam kemudian) | Tinjauan saat menulis laporan ini | Dikoreksi di laporan (§9.2) dan ke Dew |

---

# 15. Status saat laporan ditulis

**27 Sep 2026, 04:35 UTC**

| | |
|---|---|
| Forward test mulai | 26 Sep 2026 (ETH, BNB, XRP, DOGE, AVAX) · 27 Sep 2026 (NEAR) |
| Lilin terakhir diproses | 27 Sep 00:00 UTC (tutup 04:00), pada 04:00:46 |
| Sinyal | 0 |
| Trade | 0 · progres 0/100 |
| Posisi terbuka | 0 |
| Equity kertas | $300,00 |
| Versi mesin | `snap-v2-fwd-1.3.0` |
| Telegram | ✅ tes terkirim 04:35 UTC |
| Google Sheets | ✅ 4 tab, baca-balik OK |
| CI | ✅ 43/43 |
| Pemantau | Aktif. Job yang berjalan saat laporan ditulis dimulai sebelum secret lengkap; job berikutnya (±06:40 UTC) membaca secret lengkap, sebelum lilin 08:00 UTC tutup |
| Slot TRX & TAO | Dibiarkan kosong di `position.json`, tidak diproses |

Riwayat versi mesin: `1.0.0` (26 Sep, 5 koin) → `1.1.0` (8 koin, sumber per koin)
→ `1.2.0` (6 koin final) → `1.3.0` (template Telegram Dew + Google Sheets).
Rincian di [`CHANGELOG.md`](../CHANGELOG.md).

---

# 16. Peta file repo

| Path | Isi |
|---|---|
| `README.md` | Ringkasan, aturan, cara menyalakan |
| `CHANGELOG.md` | Setiap perubahan aturan / pencatatan, dengan tanggal dan alasan |
| `config.yaml` | Parameter strategi terkunci + modal kertas |
| `requirements.txt` | Versi library dipin (sama dengan MEX) + `google-auth` |
| `run_signal.py` | Driver sinyal: data → strategi → log → outbox → Telegram |
| `run_heartbeat.py` | Heartbeat harian + sinkron Sheets |
| `snap/strategy.py` | 8 syarat (salinan loop riset + EMA200) dan mesin posisi paper |
| `snap/indicators.py` | EMA, SMA, RMA, RSI Pine-faithful (dari MEX) |
| `snap/datafeed.py` | Watchlist, sumber utama per koin (`PRIMARY`), pengambilan & sanity check |
| `snap/notify.py` | Template dan pengiriman Telegram |
| `snap/ledger.py` | CSV, rotasi header, riwayat, state JSON atomik, cermin Sheets |
| `snap/sheets.py` | Google Sheets via service account (dari MEX) + baca/sinkron/tulis |
| `snap/report.py` | Tab `ringkasan` + sinkron penuh |
| `snap/stats.py` | Ringkasan hasil + pemeriksaan aturan berhenti |
| `snap/state.py` | Bentuk `position.json`, kunci dedup |
| `snap/config.py` | Pemuat config yang menolak kunci asing; `ENGINE_VERSION` |
| `snap/compat.py` | Shim pyarrow untuk laptop Windows Dew (dari MEX) |
| `tools/save_state.sh`, `refresh_state.sh`, `merge_state.py` | Penyimpanan state tahan konflik (dari MEX) |
| `tools/measure_spot_vs_perp.py` | Replikasi Report + tracking error per koin |
| `tools/send_test.py` | Pesan tes Telegram |
| `tools/sheets_check.py` | Tes tulis + baca balik Google Sheets |
| `tests/test_strategy.py` | 21 tes strategi |
| `tests/test_infra.py` | 22 tes pipa |
| `tests/reference/research_strategy.py` | `strategy.py` riset apa adanya — oracle parity |
| `pine/SequenceSnap_v2.pine` | Script TradingView v2 untuk verifikasi visual |
| `forward_test_log.csv` | Template untuk fill manual (dengan kolom `ema200_bar0`) |
| `state/` | **Bukti forward test** |
| `docs/Sequence Snap Report Trading Strategy.md` | Report riset |
| `docs/PROJECT_LOG_Sequence-Snap.md` | Jejak riset |
| `docs/FORWARD_TEST_V2_SETUP.md` | Setup forward test V2 |
| `docs/SPOT_VS_PERP.md` | Hasil pengukuran tracking error (dibuat workflow) |
| `docs/LAPORAN_PROJECT_FORWARD_TEST.md` | **Dokumen ini** |
| `docs/arsip/FORWARD_TEST_V1_SETUP.md` | Setup V1 yang digantikan |

---

# 17. Perawatan: cara mengubah sesuatu tanpa merusak eksperimen

## 17.1 Aturan emas

1. **Parameter strategi tidak diubah.** Kalau terpaksa: tulis di CHANGELOG,
   naikkan `ENGINE_VERSION`, dan anggap hasil sebelum/sesudah dua eksperimen.
2. **Jangan menyentuh `state/` dengan tangan** saat pemantau berjalan.
3. **Semua perubahan kode lewat CI hijau** (`python tests/test_strategy.py` dan
   `python tests/test_infra.py`).

## 17.2 Resep umum

| Mau | Caranya |
|---|---|
| Kirim heartbeat sekarang | Actions → "Sequence Snap heartbeat" → Run workflow → centang `force` |
| Tes Telegram + Sheets | Actions → "Kirim pesan tes" |
| Ukur ulang tracking | Actions → "Ukur spot vs perp" |
| Nyalakan pemantau manual | Actions → "Sequence Snap signal" → mode `loop` |
| Ganti sumber data satu koin | Ukur dulu; ubah `PRIMARY` di `snap/datafeed.py`; CHANGELOG; naikkan versi. Pastikan koin itu tidak sedang punya posisi |
| Tambah/keluarkan koin | Ubah `SYMBOLS` + `PRIMARY` (+ `GATE`); cek `position.json` bahwa koin itu kosong; CHANGELOG. Koin baru bootstrap flat otomatis |
| Ubah template Telegram | `snap/notify.py`; render dulu; tes infra harus hijau |
| Jalankan tes lokal | `pip install -r requirements.txt && python tests/test_strategy.py && python tests/test_infra.py` |

## 17.3 Kalau ada yang rusak

| Gejala | Cek pertama |
|---|---|
| Heartbeat tidak datang | Tab Actions: ada run "Sequence Snap signal" yang berjalan? Jalankan manual mode `loop` |
| Pesan tidak datang tapi heartbeat datang | `state/runs.csv` kolom `telegram`; outbox di `position.json` |
| Sheets tidak bertambah | `runs.csv` kolom `sheet` (`ok` / `failed` / `incomplete` / `unreachable`); jalankan "Kirim pesan tes" |
| "data tidak terjangkau" di heartbeat | Sumber cadangan otomatis mengambil alih; kalau keduanya mati beberapa hari, pertimbangkan sumber ketiga |
| `state_error` | `position.json` rusak — bot sengaja berhenti; pulihkan dari commit sebelumnya di git history |

---

# 18. Penilaian akhir dan conviction

| Pertanyaan | Conviction | Alasan |
|---|---:|---|
| Mesin bot menghitung sinyal **persis** seperti riset | **95%** | Replikasi Report persis; 185/186 trade V1; parity langsung lulus. Sisa 5%: kasus tepi yang tidak muncul di data uji |
| Bot akan menangkap & mencatat ~semua lilin selama 2 tahun | **80%** | Pola pemantau terbukti di MEX dan di sini; tapi bergantung pada GitHub cron, aturan 60 hari, dan API pihak ketiga |
| Sinyal bot = sinyal Binance futures | **~88%** per sinyal (terukur) | Tracking error tak terhindarkan dari runner GitHub |
| Versi 2 akan menunjukkan expectancy positif di forward test | **Saya tidak tahu** | Riset: ~55% bahwa entry ini punya *sedikit* edge di atas acak; V3 t = 1,99 dengan CI lebar. 100 trade pun hanya ~1,5 SE untuk +0,19 R |
| Konfigurasi ini layak diberi uang sungguhan **sekarang** | **~10%** | Sama dengan riset. Forward test inilah yang bisa mengubah angka ini |

**Kesimpulan satu kalimat:** infrastruktur forward test ini sudah terbukti
menjalankan strategi yang sama persis dengan riset, cepat, dan tercatat lengkap;
yang belum terbukti — dan memang hanya bisa dijawab oleh 2–2,5 tahun data
masa depan — adalah apakah strateginya sendiri punya edge.

---

# Lampiran

## L1. Glosarium

| Istilah | Arti |
|---|---|
| **R** | Satuan risiko. 1R = jarak entry ke stop = $3 di modal kertas ini |
| **Expectancy** | Rata-rata R per trade |
| **In-sample / out-of-sample** | Data yang dipakai membangun strategi / data yang belum pernah dilihat |
| **Versi 1 / 2 / 3** | Pola saja / pola + EMA200 (2024–26) / pola + EMA200 di 2021–23 |
| **Tracking error** | Perbedaan sinyal karena bot memakai data berbeda dari backtest |
| **Kecocokan sinyal** | cocok ÷ (sinyal futures + sinyal palsu) |
| **Bootstrap** | Run pertama koin: mulai flat dari lilin terbaru, tanpa memutar ulang sejarah |
| **Outbox** | Antrean pesan yang belum diterima Telegram |
| **Pemantau** | Job GitHub Actions yang hidup ~5,5 jam dan mengecek sendiri |
| **MAE / MFE** | Pergerakan terburuk / terbaik terhadap entry selama posisi terbuka |
| **Breadth efektif** | Berapa koin "independen" yang sebenarnya ada, mengingat korelasi |

## L2. Secret — ringkas

```
TELEGRAM_BOT_TOKEN           token bot khusus repo ini
TELEGRAM_CHAT_ID             angka saja, mis. 123456789 (grup: -100…)
GOOGLE_SERVICE_ACCOUNT_JSON  isi file kunci JSON
GSHEET_SPREADSHEET_ID        bagian URL antara /d/ dan /edit
```
Spreadsheet wajib dibagikan (Editor) ke
`crypto-sequence-snap@crypto-sequence-snap.iam.gserviceaccount.com`.

## L3. Sumber utama per koin (`snap/datafeed.py`)

```python
SYMBOLS = ["ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "NEARUSDT"]
PRIMARY = {
    "ETHUSDT":  "binance_spot_mirror",   # 87,5%
    "BNBUSDT":  "binance_spot_mirror",   # 82,8%
    "XRPUSDT":  "binance_spot_mirror",   # 90,0%
    "DOGEUSDT": "gate_io_perp",          # 100%
    "AVAXUSDT": "gate_io_perp",          # 90,0%
    "NEARUSDT": "gate_io_perp",          # 92,9%
}
```

## L4. Daftar 43 tes

**Strategi (`tests/test_strategy.py`, 21):**
`test_contoh_report_bagian3_lolos_pola`, `test_contoh_report_level_stop_target`,
`test_syarat1_lilin_merah_ketat`, `test_syarat2_semua_hijau`,
`test_syarat3_low_sama_persis_gagal`, `test_syarat4_batas_toleransi_persis_gagal`,
`test_syarat4_hanya_empat_pasang`, `test_syarat8_ema200_ketat`,
`test_versi2_memblokir_contoh_report_di_bawah_ema`, `test_parity_dengan_kode_riset`,
`test_rsi_pakai_rma_bukan_ema`, `test_ema_seed_sma`, `test_stop_kena`,
`test_target_kena`, `test_stop_dan_target_satu_lilin_stop_duluan`,
`test_gap_di_bawah_stop_terisi_di_open`, `test_gap_di_atas_target_terisi_di_open`,
`test_tidak_kena_apa_apa_tahan_terus`, `test_alur_lengkap_sinyal_entry_exit`,
`test_entry_di_open_bar_berikutnya_dan_qty`, `test_hasil_trade_contoh_report`

**Pipa (`tests/test_infra.py`, 22):**
`test_bootstrap_flat_tanpa_sinyal_basi`, `test_sinyal_entry_exit_terkirim_sekali`,
`test_telegram_gagal_tetap_di_outbox_lalu_terkirim_sekali`,
`test_feed_mundur_last_bar_tidak_mundur`,
`test_satu_simbol_mati_tidak_menjatuhkan_lainnya`, `test_semua_feed_mati_job_merah`,
`test_state_rusak_tidak_ditimpa`, `test_sinyal_basi_dicatat_tapi_tidak_dikirim`,
`test_heartbeat_sekali_sehari`, `test_merge_state_isi_bukan_sisi`,
`test_stats_aturan_berhenti`, `test_format_harga_koin_murah`,
`test_config_menolak_kunci_asing_dan_short`, `test_config_default_sama_dengan_report`,
`test_tiap_koin_punya_sumber_utama_yang_sah`, `test_fetch_mencoba_sumber_utama_dulu`,
`test_sanity_check_menolak_bolong_dan_basi`,
`test_sheets_setengah_terisi_memberi_petunjuk`,
`test_sheets_mencerminkan_ke_tab_yang_benar`, `test_sheets_mati_tidak_menghalangi_csv`,
`test_ringkasan_berisi_semua_yang_dibutuhkan`,
`test_riwayat_log_termasuk_arsip_setelah_header_berubah`

## L5. Riwayat commit utama

| Commit | Waktu (UTC) | Isi |
|---|---|---|
| `d495568` | 26 Sep 19:32 | Forward test Sequence Snap Versi 2 (paper, $300) |
| `acc163d` | 27 Sep 01:42 | Ukur sumber data per koin untuk 9 koin |
| `34ee397` | 27 Sep 01:48 | Watchlist 8 koin + sumber per koin |
| `f2ef92e` | 27 Sep 02:19 | Watchlist final 6 koin |
| `545aece` | 27 Sep 02:24 | Jam pesan konsisten |
| `19918f6` | 27 Sep 02:38 | Pesan sinyal menjawab kapan / harga / kapan dilewati |
| `e4d559e` | 27 Sep 02:54 | Template sinyal ditetapkan Dew |
| `44ec0c3` | 27 Sep 03:35 | Cermin Google Sheets |
| `1269cd2` | 27 Sep 03:42 | Tab ringkasan, sinkron harian, cek baca-balik |

Ditambah commit otomatis `state: …` dari bot (tiap run yang mengubah state) dan
`docs: ukur spot vs perp …` dari workflow pengukuran.
