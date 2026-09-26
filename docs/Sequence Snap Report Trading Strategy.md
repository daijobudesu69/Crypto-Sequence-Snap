# Sequence Snap Report Trading Strategy

**Dokumen lengkap: cara kerja strategi, syarat entry untuk forward test, tiga
versi, dan hasil modal $100.**

Disusun 20 September 2026 · Data: Binance USDⓈ-M perpetual 4H
Repo: `C:\Crypto data\Sequence-Snap-Report-Trading-Strategy` · 65 test otomatis, semuanya hijau

> **Status: DITOLAK untuk uang sungguhan. Boleh forward test dengan uang kertas.**
> Conviction 20%.

---

## Daftar isi

| Bagian | Isi |
|---|---|
| 1 | Apa strategi ini, dalam bahasa biasa + analogi |
| **2** | **Tabel syarat trigger entry — lengkap** |
| 3 | Contoh sinyal nyata yang bisa diverifikasi di TradingView |
| 4 | Aturan exit, larangan, dan parameter terkunci |
| **5** | **Tiga versi: indikator / +MA200 / +MA200 di data baru** |
| **6** | **Modal $100 di tiga versi** |
| 7 | Angka operasional (posisi bersamaan, streak, funding) |
| 8 | Kenapa hasilnya begini — enam temuan, dengan analogi |
| 9 | Yang masih tidak diketahui |
| 10 | Rekomendasi & checklist forward test |

---

# BAGIAN 1 — Apa strategi ini

## Aturannya dalam satu kalimat

> Cari **satu lilin merah**, lalu **lima lilin hijau berturut-turut** yang naik
> rapi dan tidak pernah turun lagi ke bawah dasar lilin merah itu. Beli.
> Stop di dasar lilin merah, target 1,5 kali jarak stop.

## Analoginya: bola pantul

Bola jatuh (lilin merah), menyentuh lantai, lalu memantul naik lima kali
berturut-turut — dan tidak sekali pun turun kembali sampai menyentuh lantai.

Strategi ini bertaruh bahwa bola yang memantul serapi itu masih punya tenaga
naik sedikit lagi.

Lantai itu jadi batas: kalau bola akhirnya menyentuhnya lagi, taruhan ditutup
rugi.

## Namanya menyesatkan — tiga kata, tiga-tiganya tidak terbukti

Script aslinya bernama **"RSI-Confirmed Reversal Scalper"**.

| Klaim | Yang sebenarnya terukur |
|---|---|
| **RSI-Confirmed** | Filter RSI membuang **nol** dari 53 sinyal di ETH. Pola lima lilin naik secara mekanis sudah mendorong RSI naik dan melewati 40 — filternya hiasan |
| **Reversal** | Kalau benar menangkap pembalikan, ia bekerja dua arah. Sisi short: **t = 0,51** dari 432 trade. Tidak bisa dibedakan dari lempar koin |
| **Scalper** | Rata-rata pegang **6,4 hari**. Rekor: **117 hari** |

Nama yang jujur: **"beli setelah pantulan rapi, stop lebar, target 1,5R"**.

---

# BAGIAN 2 — Tabel syarat trigger entry

**Ini bagian utama untuk forward test.**

## 2.1 Cara membaca penomoran lilin

Penomoran dihitung **mundur** dari lilin yang baru saja tutup:

```
 bar 5     bar 4     bar 3     bar 2     bar 1     bar 0
(paling                                          (lilin yang
 lama)                                            BARU tutup)
  ▼         ▼         ▼         ▼         ▼         ▼
[MERAH]  [hijau]  [hijau]  [hijau]  [hijau]  [hijau]  →  ENTRY di
                                                          lilin berikutnya
```

Semua pemeriksaan dilakukan **pada saat lilin bar 0 TUTUP** — bukan saat lilin
masih berjalan.

Timeframe **4 jam**. Bar tutup di **00, 04, 08, 12, 16, 20 UTC**.

## 2.2 Syarat ENTRY LONG — delapan syarat, semua harus terpenuhi

| # | Syarat | Rumus persis | Kenapa ada |
|---|---|---|---|
| **1** | Lilin bar 5 harus **MERAH** | `close[5] < open[5]` (kurang dari — sama dengan = GAGAL) | Ini "jatuhnya bola", titik acuan pantulan |
| **2** | Lilin bar 0, 1, 2, 3, 4 semua harus **HIJAU** | `close[i] > open[i]` untuk i = 0,1,2,3,4 | Lima pantulan berturut-turut tanpa jeda |
| **3** | Dasar semua lilin hijau harus **DI ATAS** dasar lilin merah | `low[i] > low[5]` untuk i = 0,1,2,3,4 — **menyentuh sama persis = GAGAL** | Bola tidak pernah turun lagi ke lantai |
| **4** | Tiap lilin hijau tutup **lebih tinggi** dari lilin sebelumnya, boleh meleset maks 0,05% | `close[i] > close[i+1] × 0,9995` untuk i = **0,1,2,3 saja** | Toleransi goyangan kecil |
| **5** | Momentum cukup kuat | `RSI(14) di bar 0 > 40` | Filter momentum |
| **6** | Momentum sedang naik | `RSI(14) bar 0 > RSI(14) bar 1` | Filter momentum |
| **7** | Tidak sedang punya posisi di koin itu | `posisi = 0` | Tidak boleh menumpuk posisi |
| **8** | **(Versi 2 & 3 saja)** Harga di atas garis tren | `close[0] > EMA200` | Filter tren — lihat Bagian 5 |

### Tiga jebakan di tabel ini

**Syarat 3 — "menyentuh sama persis = GAGAL".** Rumus Pine-nya `low[i] <= low[5]`
membatalkan sinyal. Jadi kalau ada lilin hijau yang low-nya **persis sama** dengan
low lilin merah, pola itu batal. Bukan "lebih rendah", tapi "lebih rendah atau
sama".

**Syarat 4 — hanya 4 pasang, bukan 5.** Yang dibandingkan:

| Pasangan | Dibandingkan |
|---|---|
| i = 3 | close bar 3 vs close bar 4 |
| i = 2 | close bar 2 vs close bar 3 |
| i = 1 | close bar 1 vs close bar 2 |
| i = 0 | close bar 0 vs close bar 1 |

Pasangan **bar 4 vs bar 5 TIDAK PERNAH diperiksa**, karena bar 5 adalah lilin
merah — bukan bagian dari pantulan.

**Syarat 4 — arah indeksnya mundur.** `close[i+1]` artinya lilin yang **lebih
lama**, bukan lebih baru. Ini sumber kesalahan paling umum saat
mengimplementasikan ulang.

## 2.3 Level stop, target, dan harga entry

| Yang dihitung | Rumus | Catatan |
|---|---|---|
| **Stop loss** | `low[5]` — dasar lilin merah | Angka mati. **Tidak ada trailing** |
| **Risk (jarak risiko)** | `close[0] − low[5]` | Dari **close bar 0**, bukan dari harga entry |
| **Take profit** | `close[0] + (risk × 1,5)` | Juga dari close bar 0 |
| **Harga entry** | **Open lilin BERIKUTNYA**, market order | **BUKAN** close bar 0 |
| **Ukuran posisi** | `(modal × 1%) ÷ (harga entry − stop)` | Risiko tetap 1% equity |

**Yang paling sering salah:** stop dan target dihitung dari harga **tutup** lilin
sinyal, tapi masuknya di harga **buka** lilin berikutnya. Di crypto bedanya kecil
(median cuma 0,01%, karena pasar buka 24 jam tanpa gap sesi), tapi aturannya
tetap harus diikuti persis supaya hasilnya bisa diadu dengan backtest.

---

# BAGIAN 3 — Contoh sinyal nyata untuk verifikasi

Ini sinyal asli ETHUSDT 4H. Dew bisa buka TradingView, lompat ke tanggal ini, dan
cocokkan angkanya satu per satu. **Kalau hasil Dew berbeda, ada yang belum sinkron
— bereskan dulu sebelum forward test mulai.**

**Bar sinyal: 9 September 2024, 08:00 UTC**

| Label | Waktu buka (UTC) | Open | High | Low | Close |
|---|---|---:|---:|---:|---:|
| bar 5 | 2024-09-08 12:00 | 2295,28 | 2298,16 | **2238,88** | 2244,67 |
| bar 4 | 2024-09-08 16:00 | 2244,68 | 2282,59 | 2242,17 | 2270,63 |
| bar 3 | 2024-09-08 20:00 | 2270,64 | 2333,98 | 2266,46 | 2295,89 |
| bar 2 | 2024-09-09 00:00 | 2295,90 | 2320,00 | 2286,59 | 2303,34 |
| bar 1 | 2024-09-09 04:00 | 2303,33 | 2315,95 | 2281,04 | 2313,03 |
| bar 0 | 2024-09-09 08:00 | 2313,03 | 2338,74 | 2308,00 | **2314,10** |

## Pengecekan delapan syarat

| # | Cek | Perhitungan | Hasil |
|---|---|---|---|
| 1 | bar 5 merah | 2244,67 < 2295,28 | **LULUS** |
| 2 | bar 0–4 hijau | 2270,63>2244,68 · 2295,89>2270,64 · 2303,34>2295,90 · 2313,03>2303,33 · 2314,10>2313,03 | **LULUS** |
| 3 | low bar 0–4 > 2238,88 | 2242,17 · 2266,46 · 2286,59 · 2281,04 · 2308,00 | **LULUS** |
| 4a | bar 3 vs bar 4 | 2295,89 > 2270,63 × 0,9995 = **2269,49** | **LULUS** |
| 4b | bar 2 vs bar 3 | 2303,34 > 2295,89 × 0,9995 = **2294,74** | **LULUS** |
| 4c | bar 1 vs bar 2 | 2313,03 > 2303,34 × 0,9995 = **2302,19** | **LULUS** |
| 4d | bar 0 vs bar 1 | 2314,10 > 2313,03 × 0,9995 = **2311,87** | **LULUS** |
| 5 | RSI(14) > 40 | 48,52 > 40 | **LULUS** |
| 6 | RSI naik | 48,52 > 48,33 | **LULUS** |

## Perhitungan order

```
stop    = 2238,88                                (low bar 5)
risk    = 2314,10 − 2238,88 = 75,22              (3,25% dari harga)
target  = 2314,10 + 1,5 × 75,22 = 2426,93
entry   = open lilin 2024-09-09 12:00 = 2314,09
qty     = (modal × 1%) ÷ (2314,09 − 2238,88)
```

**Hasilnya:** target kena di 2426,92 setelah 25 bar (≈ 4 hari). **R = +1,468.**

---

# BAGIAN 4 — Exit, larangan, dan parameter

## 4.1 Aturan exit

| Kejadian | Tindakan |
|---|---|
| Harga menyentuh **stop** | Tutup posisi. Rugi ≈ 1 R |
| Harga menyentuh **target** | Tutup posisi. Untung ≈ 1,5 R |
| Dua-duanya kena di lilin yang sama | Asumsikan **stop duluan** (pesimis). Di backtest ini **tidak pernah terjadi** — 0 dari 1.927 trade |
| Tidak kena apa-apa | **Tahan terus. Tidak ada batas waktu** |

**Peringatan:** karena tidak ada batas waktu, posisi bisa menggantung sangat lama.
Rekor di backtest **117 hari** (1000BONK, Feb–Jun 2026). Median jauh lebih pendek
(2,8 hari), tapi Dew harus siap dengan ekor panjang ini.

## 4.2 Yang JANGAN dilakukan — semuanya sudah diuji dan gagal

| Larangan | Bukti |
|---|---|
| **Jangan pakai sisi SHORT** | 432 trade: expectancy +0,030 R, **t = 0,51**. Tidak bisa dibedakan dari lempar koin |
| **Jangan pakai trailing stop** | Diuji 2 varian. Drawdown justru **lebih dalam**: 37,9 R dan **59,4 R** vs 33,5 R baseline |
| **Jangan tambah filter VixFix** | 514 trade. Korelasi dengan menang/kalah: **+0,006 (p = 0,90)**. Nol informasi |
| **Jangan tambah SuperTrend** | Tidak menambah nilai (p = 0,50) |
| **Jangan tambah filter "trending" (ADX)** | Justru **MERUGIKAN** — R/DD jatuh dari 2,83 ke 1,48 |
| **Jangan ubah target 1,5R** | Tidak diuji, dan mengujinya = mencari angka yang enak dilihat |
| **Jangan pyramiding** | Satu posisi per koin. Titik |

## 4.3 Parameter — kunci semuanya

```yaml
timeframe          : 4 jam (bar tutup 00,04,08,12,16,20 UTC)
instrumen          : Binance USDⓈ-M perpetual futures
run_length         : 5        (jumlah lilin hijau)
tolerance_pct      : 0.05     (persen)
rsi_length         : 14
rsi_min_long       : 40
take_profit_r      : 1.5
allow_short        : false    ← JANGAN diubah
komisi             : 0,05% per sisi
slippage asumsi    : 1 tick
risiko per trade   : 1% equity
ema_length         : 200      (hanya Versi 2 & 3)
```

---

# BAGIAN 5 — Tiga versi

| | **Versi 1** | **Versi 2** | **Versi 3** |
|---|---|---|---|
| Aturan | Indikator saja | Indikator + MA200 | Indikator + MA200 |
| Syarat entry | 1–7 | 1–**8** | 1–**8** |
| Periode uji | 2024-01 → 2026-09 | 2024-01 → 2026-09 | **2021-01 → 2023-12** |
| Sifat periode | **dipakai membangun** strategi | **dipakai membangun** strategi | **belum pernah dilihat** |
| Koin | 15 | 15 | 8 |

**Versi 3 bukan strategi yang berbeda dari Versi 2.** Aturannya sama persis. Yang
berbeda hanya periodenya.

## Kenapa perbedaan itu menentukan segalanya

**Analogi ujian.** Versi 1 dan 2 diukur di periode yang sama dengan yang dipakai
menemukan strategi — itu ujian dengan soal yang sudah dibahas di kelas. Nilainya
pasti bagus, dan tidak memberi tahu apa pun tentang ujian berikutnya.

Versi 3 adalah ujian dengan soal baru, termasuk bear market 2022.

**Hanya angka Versi 3 yang punya arti sebagai perkiraan hasil ke depan.**
Versi 1 dan 2 adalah batas atas yang optimis.

## 5.1 Hasil pokok

| | Versi 1 | Versi 2 | **Versi 3** |
|---|---:|---:|---:|
| Trade | 503 | 315 | 168 |
| Trade per bulan | 15,4 | 9,7 | 4,7 |
| Win rate | 48,7% | 51,7% | 49,4% |
| **Expectancy** | +0,1855 R | **+0,2584 R** | +0,1915 R |
| Standard error | 0,056 | 0,070 | 0,096 |
| **t-statistic** | 3,34 | **3,67** | **1,99** |
| R per tahun | +34,35 | +29,97 | +10,74 |
| **Max drawdown** | 33,52 R | 20,55 R | **11,79 R** |
| Rasio R/DD | 2,78 | **3,96** | 2,73 |
| Koin yang untung | 11/15 | 12/15 | **8/8** |

## 5.2 Perbandingan adil — koin yang sama persis (8 koin)

Universe berbeda antar versi (5 koin belum listing di 2021), jadi tabel ini
memakai 8 koin yang sama di semua kolom.

| | V1 di 2024–26 | V2 di 2024–26 | **V2 di 2021–23 (=V3)** | **V1 di 2021–23** |
|---|---:|---:|---:|---:|
| Trade | 290 | 189 | 168 | 273 |
| **Expectancy** | +0,2136 R | +0,2707 R | **+0,1915 R** | **−0,0053 R** |
| **t** | 2,92 | 2,98 | **1,99** | **−0,07** |
| R per tahun | +22,81 | +18,84 | +10,74 | **−0,49** |
| Max DD | 21,03 R | 11,53 R | 11,79 R | **31,71 R** |
| R/DD | 2,95 | **4,44** | 2,73 | **−0,05** |

**Kolom paling kanan adalah alasan filter MA200 ada di dokumen ini.**

Tanpa MA200, di periode yang belum pernah dilihat, strategi menghasilkan **nol**
(t = −0,07) sambil tetap menanggung drawdown penuh 31,71 R. Dengan MA200, ia masih
menghasilkan +0,19 R per trade dengan drawdown kurang dari separuhnya.

## 5.3 Hasil per tahun

| Tahun | Versi 1 | Versi 2 | Versi 3 (data baru) |
|---|---:|---:|---:|
| 2021 | — | — | **+22,79 R** (70 trade) |
| **2022 (bear)** | — | — | **−10,12 R** (32 trade) |
| 2023 | — | — | **+19,50 R** (66 trade) |
| 2024 | +18,27 R (194) | +34,53 R (137) | — |
| 2025 | +58,73 R (206) | +33,48 R (111) | — |
| 2026 (s/d Sep) | +16,29 R (103) | +13,39 R (67) | — |

**Baris 2022 adalah argumen praktis terkuat untuk MA200.** Di bear market itu,
versi **tanpa** MA200 rugi **−28,48 R** dari 89 trade. Versi **dengan** MA200
rugi **−10,12 R** dari 32 trade — filter itu memotong kerusakan sekitar dua
pertiga, terutama dengan cara **tidak masuk sama sekali**.

## 5.4 Peringatan jujur tentang MA200

Filter MA200 **ditolak** di uji formal, dan alasannya masih berlaku:

| Uji | Hasil |
|---|---|
| Koreksi multiple testing (5 filter diuji) | p = 0,040 × 5 = **0,200 — TIDAK LOLOS** |
| Kontribusi di dalam rezim pasar yang sama | p = 0,190 (bull) / 0,390 (bear) — **tidak signifikan** |
| Apakah penurunan drawdown-nya nyata? | **TIDAK.** Membuang 43% trade secara acak menghasilkan drawdown yang justru **lebih kecil** (median 21,1 R vs 22,5 R milik MA200) |

Lalu kenapa masih dipakai? Karena **out-of-sample ia bertahan dan versi polos
tidak.** Tapi ada jebakan logika yang harus disebut: memilih MA200 *karena* ia
bertahan di OOS berarti memakai data OOS untuk memutuskan — dan itu mengubah OOS
jadi in-sample.

**Status jujurnya: MA200 adalah hipotesis yang belum terbukti, bukan filter yang
sudah tervalidasi. Forward test inilah ujian ketiganya yang benar-benar bersih.**

---

# BAGIAN 6 — Modal $100 di tiga versi

## 6.1 Hambatan yang muncul di modal kecil

Dengan modal $100 dan risiko 1% ($1 per trade), dan jarak stop rata-rata ~6% dari
harga, ukuran posisinya cuma **~$16 notional**.

Binance menolak order di bawah nilai minimum (MIN_NOTIONAL):

| Koin | Minimum |
|---|---|
| BTC | $50 |
| ETH, BCH, LINK | $20 |
| Koin lain | $5 |

Akibatnya di modal $100, sebagian besar sinyal **tidak bisa dieksekusi sama
sekali** — terutama di koin besar, yang justru penyumbang terbesar.

| Versi | Trade yang bisa jalan di $100 | Ditolak | Nilai yang hilang |
|---|---|---:|---:|
| Versi 1 | 382 dari 503 | 121 | +15,2 R |
| Versi 2 | 229 dari 315 | 86 | +15,7 R |
| Versi 3 | 89 dari 168 | **79 (47%)** | +18,7 R |

*Nilai MIN_NOTIONAL di atas dari snapshot exchangeInfo 7 Sep 2026 dan berstatus
**asumsi** — `fapi.binance.com` tidak bisa dijangkau dari mesin ini untuk
verifikasi ulang. Dew sebaiknya cek sendiri di akun sebelum mulai.*

## 6.2 Hasil modal $100 setelah 1 tahun

Angka di bawah **sudah memperhitungkan**: komisi 0,05% dua sisi, slippage 1 tick,
biaya funding, dan order yang ditolak karena MIN_NOTIONAL.

| | **Versi 1** | **Versi 2** | **Versi 3** |
|---|---:|---:|---:|
| Trade per bulan yang bisa jalan | ~11,7 | ~7,0 | ~2,5 |
| **$100 setelah 1 tahun** | **$128,77** | **$124,19** | **$104,49** |
| Dengan compounding | $129,10 | $125,19 | $104,30 |
| CAGR | +29,1% | +25,2% | **+4,3%** |
| **Drawdown terdalam** | **−23,9%** | −14,2% | **−6,4%** |
| **Rentang 95% setelah 1 thn** | $111 – $146 | $111 – $138 | **$97 – $112** |

### Cara membacanya

- **Versi 1 ($128,77)** dan **Versi 2 ($124,19)** diukur di periode yang dipakai
  membangun strategi. Anggap ini **batas atas**, bukan perkiraan.
- **Versi 3 ($104,49)** adalah satu-satunya angka yang berperan sebagai perkiraan
  ke depan. **$100 jadi sekitar $104 setelah setahun** — untung $4,49, dengan
  kemungkinan berkisar antara **rugi $3 sampai untung $12**.

Untuk $4,49 setahun, Dew memantau 8 koin dan mengeksekusi sekitar 30 trade.

## 6.3 Kalau modalnya lebih besar

Hambatan MIN_NOTIONAL hilang di modal lebih besar, dan hasilnya membaik nyata:

| Modal | Versi 1 | Versi 2 | **Versi 3** |
|---|---:|---:|---:|
| **$100** | $128,77 (+28,8%) | $124,19 (+24,2%) | **$104,49 (+4,5%)** |
| **$300** | $404,09 (+34,7%) | $390,32 (+30,1%) | **$332,06 (+10,7%)** |
| **$1.000** | $1.343 (+34,3%) | $1.300 (+30,0%) | **$1.107 (+10,7%)** |
| Drawdown di $1.000 | −30,7% | −19,8% | **−12,9%** |

**Modal sekitar $300 adalah ambang di mana hampir semua sinyal bisa dieksekusi.**
Di bawah itu Dew kehilangan trade-trade terbaik — Versi 3 jatuh dari +10,7% ke
+4,5% semata karena order ditolak bursa, bukan karena strateginya berbeda.

## 6.4 Kalau hanya ETH, SOL, BNB

Perlu dicatat: tiga koin ini dipilih **setelah** melihat hasilnya, jadi angkanya
lebih optimis dari yang pantas.

| | V1 (3 koin) | V2 (3 koin) | **V3 (ETH+BNB)** |
|---|---:|---:|---:|
| Trade | 112 | 83 | 54 |
| Trade per bulan | 3,4 | 2,5 | 1,5 |
| Expectancy | +0,3015 R | +0,2849 R | +0,1298 R |
| **t** | 2,56 | 2,08 | **0,77** |
| **$100 setelah 1 thn** | **$108,47** | **$106,73** | **$101,07** |
| Drawdown | −11,8% | −9,7% | −7,5% |

*(SOL tidak ada di uji out-of-sample — datanya bolong 30 bar di 2022, dikeluarkan
sesuai aturan validasi.)*

Di data baru, tiga koin saja memberi **t = 0,77** — tidak bisa dibedakan dari nol,
dan $100 jadi $101. Lebih sedikit koin berarti lebih sedikit sinyal, dan dengan
sinyal sesedikit itu tidak ada cara membedakan keberuntungan dari kemampuan.

---

# BAGIAN 7 — Angka operasional

Hal-hal yang tidak terlihat dari tabel expectancy, tapi menentukan apakah
strateginya bisa dijalankan sungguhan.

## 7.1 Berapa posisi terbuka bersamaan

| | Versi 1 | Versi 2 | **Versi 3** |
|---|---:|---:|---:|
| Maksimum posisi bersamaan | 12 | 12 | **5** |
| Median | 4 | 3 | 2 |
| Persentil 95 | 9 | 8 | 4 |
| **Risiko serentak maksimum** | **12% equity** | **12% equity** | **5% equity** |

Dengan risiko 1% per posisi, Versi 1 dan 2 pernah punya **12% equity
dipertaruhkan sekaligus**. Margin harus cukup, dan Dew harus siap melihat 12
posisi merah bersamaan.

## 7.2 Diversifikasi yang sebagian besar ilusi

**Analogi:** Anda kira punya 15 keranjang telur. Ternyata 15 keranjangnya ditaruh
di satu truk.

| | Nilai |
|---|---|
| Korelasi return harian antar koin | rata-rata **0,62** (min 0,40, maks 0,82) |
| Satu faktor menjelaskan | **65,2%** dari seluruh varians |
| **Breadth efektif** | **~1,5 dari 15 koin** |

Menambah koin **tidak** mengecilkan drawdown — mereka rugi berbarengan.

## 7.3 Deret kekalahan dan lama menahan posisi

| | Versi 1 | Versi 2 | **Versi 3** |
|---|---:|---:|---:|
| **Streak kalah terpanjang** | 12 | 12 | **7** |
| Holding median | 2,8 hari | 2,7 hari | 3,0 hari |
| Holding persentil 90 | 14 hari | 12,5 hari | 15,5 hari |
| Holding maksimum | **117 hari** | 74 hari | 39 hari |

Dua belas kekalahan beruntun sudah cukup membuat kebanyakan orang berhenti. Ini
terjadi di backtest yang hasil akhirnya positif — jadi harus dianggap **normal**,
bukan tanda strateginya rusak.

## 7.4 Hal teknis yang mudah salah di bot

| Hal | Yang benar | Risiko kalau salah |
|---|---|---|
| **Interval funding** | **Tidak seragam.** 1000BONK dan TIA tiap **4 jam**; 13 koin lain tiap 8 jam | Kalau 8 jam di-hardcode, biaya dua koin itu terhitung setengahnya |
| Biaya funding | +0,012 R per trade (~6% expectancy). 13,8% trade justru **menerima** | Mengabaikannya melebih-lebihkan hasil ~6% |
| **Smoothing RSI** | **RMA (Wilder)**, bukan EMA | Filter `rsi > 40` ada persis di wilayah sensitif |
| Timestamp bar | `open_time`, milidetik, **UTC** = waktu **buka** bar | Salah timezone = semua sinyal geser |
| Tick size | ETH 0,01 — **diturunkan** dari desimal harga arsip, bukan dari exchangeInfo | Kecil di ETH, bisa berarti di koin murah |
| Harga entry | Open lilin berikutnya, market order | Pakai close bar sinyal = hasil tidak akan cocok |

---

# BAGIAN 8 — Kenapa hasilnya begini: enam temuan

## 8.1 Lolos uji "lebih baik dari asal masuk" — tapi separuhnya mekanis

**Analogi.** Anda klaim bisa main basket. Kami suruh 1.000 orang tutup mata
melempar 43 kali. Skor Anda mengalahkan **semuanya**.

Lalu kami sadar Anda melempar dari dekat ring sementara mereka dari titik acak
yang jauh. Kami samakan jaraknya. Anda masih menang — tapi kali ini ada **satu**
orang buta yang mengalahkan Anda.

| | Nilai |
|---|---|
| Persentil vs 1.000 entry acak | **100,0** |
| Persentil setelah lebar stop disetarakan | **99,9** |
| Jarak stop strategi vs bar acak | **2,81× ATR** vs 1,04× ATR |
| R per trade entry acak — semua bar | −0,223 |
| R per trade entry acak — **lebar stop disetarakan** | **−0,001 (impas)** |

**Sekitar 40% keunggulannya hilang begitu lebar stop disetarakan.** Stop yang
lebar memberi keuntungan mekanis, bukan prediksi.

## 8.2 Sepertiga profitnya cuma "long di pasar yang naik"

Sejarah harga dipotong jadi blok 20 lilin, diacak urutannya, disusun ulang jadi
1.000 grafik palsu. Di grafik yang polanya sudah tidak ada apa-apa lagi, strategi
**tetap** menghasilkan rata-rata **+6,70 R** dari +22,03 R yang dicapai di grafik
asli.

Sebabnya: pengacakan mempertahankan **rata-rata** kenaikan. ETH naik sepanjang
periode, jadi grafik palsunya juga naik. Strategi long-only untung tanpa perlu
memprediksi apa pun.

## 8.3 Jalan di 12 dari 15 koin — dan satu hasil yang benar-benar bagus

| | Nilai |
|---|---|
| Koin dengan expectancy positif | **12 dari 15** |
| **Top 5 pemenang** | **2,0% dari profit kotor** |
| Total R tanpa top 5 | +103,73 dari +111,22 |

**Analogi terbalik.** Restoran yang 77% omzetnya dari 5 pelanggan bukan restoran,
itu taruhan. Di sini kebalikannya — keuntungannya tersebar merata di ratusan
trade. **Ini salah satu hasil terkuat di seluruh penelitian.**

## 8.4 Keuntungannya runtuh di luar pasar naik — dan sisi short nol

**Analogi.** Obat yang diklaim menyembuhkan demam, tapi ternyata hanya bekerja
saat cuaca hangat. Itu bukan obat demam, itu selimut.

| Kelompok | Trade | Expectancy | t |
|---|---:|---:|---:|
| BTC di atas SMA200 | 234 | **+0,397 R** | 4,96 |
| BTC di bawah SMA200 | 281 | **+0,065 R** | **0,88** |
| Sisi short | 432 | +0,030 R | **0,51** |

Kalau polanya benar-benar menangkap pembalikan arah, ia bekerja dua arah. Tidak.

## 8.5 Semua upaya perbaikan gagal

| Upaya | Hasil |
|---|---|
| 4 varian exit | Baseline menang telak (R/DD 2,83 vs 1,04 / 0,53 / 1,06). **Tiga alternatif runtuh ke t < 1,5** |
| Trailing stop | Drawdown justru **lebih dalam** |
| VixFix bucketing | Korelasi dengan menang/kalah **+0,006 (p = 0,90)** |
| 5 filter rezim | Nol yang lolos koreksi multiple testing |
| Penurunan drawdown MA200 | **Ditolak** — artefak jumlah trade |

Bahwa tiga cara keluar yang masuk akal semuanya menjatuhkan expectancy ke nol
adalah tanda buruk tersendiri: **edge yang kokoh tidak serapuh itu.**

## 8.6 Satu temuan palsu yang nyaris lolos

Uji rank correlation VixFix memberi **rho +0,1995, p = 0,000005**, positif di
**14 dari 15 koin**. Kalau dilaporkan apa adanya, itu terbaca sebagai penemuan.

Tapi angkanya tidak cocok dengan tetangganya (Pearson cuma +0,019, p = 0,66).
Ditelusuri:

| Korelasi VixFix dengan | rho | p |
|---|---:|---:|
| **Menang atau kalah** | **+0,006** | **0,90** |
| Jarak stop | +0,431 | 1e-24 |
| Biaya komisi dalam R | −0,425 | 6e-24 |

**Seluruh "temuan" itu adalah aritmetika biaya transaksi.** VixFix tinggi → stop
lebih lebar → posisi lebih kecil → komisi dalam R lebih kecil. Tidak ada kaitan
sama sekali dengan siapa yang menang.

---

# BAGIAN 9 — Yang masih tidak diketahui

1. **Apakah filter MA200 bertahan di periode ketiga.** Satu-satunya benang yang
   masih hidup — dan forward test inilah ujiannya.
2. **Besarnya survivorship bias.** Universe dipilih pakai likuiditas 2024–2026.
   Untuk uji 2021–2023 itu berarti menguji koin yang sudah diketahui selamat.
   Arahnya **menguntungkan** strategi — dan ia tetap gagal.
3. **Apakah edge kecil masih mungkin.** CI95 out-of-sample [−0,151 , +0,140] R
   masih memuat +0,14. "Tidak ada bukti" ≠ "terbukti tidak ada".
4. **Apakah struktur pasar berubah** antara 2021 dan 2025. Strategi yang hanya
   jalan di satu era, dan kita tidak tahu era mana yang sedang berjalan, tidak
   bisa dipakai.
5. **Slippage sesungguhnya.** Asumsi 1 tick optimis untuk koin tipis.
6. **Funding di rezim ekstrem.** 2024–2026 funding-nya jinak; di puncak euforia
   bisa jauh lebih mahal — dan di situ strategi long-only paling aktif.
7. **`tickSize` dan `MIN_NOTIONAL`** berstatus asumsi.
8. **Kenapa BTC terburuk out-of-sample** (−0,272 R) padahal in-sample positif
   (+0,243 R). Belum diselidiki.
9. **Apakah posisi 117 hari bertahan di kenyataan.** Margin, leverage tier,
   delisting — nol pemodelan.
10. **Efek korelasi antar trade terhadap semua p-value.** Breadth efektif ~1,5,
    jadi p sebenarnya lebih besar dari yang tertulis.

---

# BAGIAN 10 — Rekomendasi & checklist forward test

## 10.1 Rekomendasi

**Jangan pakai uang sungguhan.** Tidak ada satu pun uji yang lolos bersih.

Kalau Dew tetap mau forward test:

| Keputusan | Saran | Alasan |
|---|---|---|
| Versi mana | **Versi 2/3 (dengan MA200)** | Satu-satunya yang bertahan di data baru |
| Modal | **Minimal $300**, idealnya lebih | Di bawah itu MIN_NOTIONAL memakan trade terbaik |
| Jumlah koin | **8–15**, jangan 3 | Sinyal terlalu sedikit untuk belajar apa pun |
| Risiko per trade | **1%**, jangan lebih | Drawdown historis sudah 12–30% di angka ini |
| Lama | **Minimal 6 bulan**, idealnya 12 | Butuh ~100 trade sebelum angkanya berarti |
| Uang | **Paper trading dulu** | Belum ada uji yang lolos bersih |

## 10.2 Yang wajib dicatat tiap trade

| Kolom | Kenapa perlu |
|---|---|
| Koin, waktu sinyal (UTC), waktu entry | Cocokkan dengan bar 4H |
| close bar 0, low bar 5 | Verifikasi level |
| Stop, target, harga entry sebenarnya | Ukur selisih dari rencana |
| RSI(14) bar 0 dan bar 1 | Verifikasi filter |
| close vs EMA200 | Verifikasi filter Versi 2/3 |
| Qty, notional | Cek MIN_NOTIONAL |
| Harga exit, alasan exit, jumlah bar ditahan | Hasil |
| **Slippage nyata** (entry & exit) | Backtest asumsi 1 tick — cek apakah realistis |
| **Total funding dibayar** | Backtest asumsi ~0,012 R per trade |
| R hasil akhir | Metrik utama |

## 10.3 Kapan harus berhenti — tetapkan SEKARANG

| Kondisi | Tindakan |
|---|---|
| Drawdown menembus **−20%** | Berhenti, evaluasi ulang |
| **15 kekalahan beruntun** | Berhenti (rekor historis: 12) |
| Setelah **100 trade** expectancy masih negatif | Strategi ditolak |
| Slippage nyata **> 3× asumsi** | Hitung ulang semuanya — model biayanya salah |
| Ada sinyal live yang **tidak cocok** dengan backtest | Hentikan, cari sebabnya |

## 10.4 Ekspektasi yang realistis

Berdasarkan Versi 3 — satu-satunya angka out-of-sample:

- Sekitar **4–5 sinyal per bulan** di 8 koin
- Win rate sekitar **49%**
- Sekitar **setengah** bulan akan berakhir merah
- Perkiraan setahun: **+4% sampai +11%** tergantung modal, drawdown **6–13%**
- **Tahun pertama bisa flat atau rugi** — di backtest, 2024 hanya menghasilkan
  +2,3 R sambil melewati drawdown terdalamnya

## 10.5 Kesimpulan satu kalimat

Strategi ini **belum terbukti**, tapi versi ber-MA200-nya adalah satu-satunya
bagian yang selamat dari tujuh tahap pengujian — dan forward test dengan uang
kertas selama 6–12 bulan adalah cara termurah untuk tahu apakah ia nyata.

---

## Lampiran — dari mana semua angka ini

| Sumber | Isi |
|---|---|
| `experiments/` | 15 script, satu per uji. Semua seed dikunci (20260920), hasilnya deterministik |
| `results/` | Output mentah json + csv untuk tiap angka di dokumen ini |
| `reports/01` … `06` | Report per fase, lengkap dengan metode dan keberatannya |
| `PROJECT_LOG_Sequence-Snap.md` | Catatan keputusan, insiden, dan penyimpangan dari brief |
| `CHANGELOG_CONFIG.md` | Riwayat parameter — dua entri, dua-duanya sebelum eksperimen dijalankan |
| `tests/` | 65 test: parity Pine, anti-lookahead, akuntansi tertutup, determinisme |

Verifikasi cepat:

```bash
python -m pytest tests/ -q          # 65 hijau
python experiments/p7_versi_forward.py   # angka tiga versi di Bagian 5 & 6
```

**Parameter tidak pernah diubah sepanjang penelitian.**
