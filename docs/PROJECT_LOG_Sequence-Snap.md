# Project Log — Sequence Snap

Catatan lengkap bagaimana project ini sampai di sini: apa yang diuji, apa yang
diputuskan, apa yang sempat salah, dan apa yang masih tidak diketahui. Ditulis
supaya siapa pun yang memegang ini enam bulan lagi — termasuk penulisnya sendiri
— bisa merekonstruksi setiap keputusan tanpa menurunkannya ulang.

**Status: SELESAI. Strategi DITOLAK untuk uang sungguhan. Conviction 20%.**

| Fase | Yang terjadi | Hasil |
|---|---|---|
| 0. Data & engine | Inspeksi arsip, engine bar-by-bar sendiri, 65 test | **Lolos** |
| 0. Replikasi | Adu dengan angka TradingView | **Lolos** — meleset 2,3% |
| 1. Kill gate T13 | 1.000 entry acak + block bootstrap | **Lolos** — persentil 100 |
| 2. Pooled 15 koin | Parameter sama, nol tuning | **Lolos** — 12/15 positif |
| 2.5 Cek short | Sisi short dinyalakan | **GAGAL** — t = 0,51 |
| 2b. Funding | Diukur dari arsip resmi | Menggerus 6,1% |
| 3. Exit surgery | 4 varian exit | Baseline menang; 3 alternatif runtuh |
| 4. VixFix | Bucketing 5 kelompok | **Nol informasi** |
| 5. Regime ablation | 5 filter, satu per satu | **Nol yang terbukti** |
| 5b. Drawdown MA200 | Uji permutasi 10.000× | **Ditolak** |
| **6. Out-of-sample** | **2021–2023, nol parameter diubah** | **GAGAL — t = −0,07** |
| 7. Tiga versi | Terjemahan ke modal nyata | Untuk forward test |

Periode kerja: satu sesi, 20 September 2026.
Lokasi: `C:\Crypto data\Sequence-Snap-Report-Trading-Strategy`
(sebelumnya `new-edge-v1-backtest` — diganti 20 Sep 2026, nol path di kode ikut
berubah karena semua script memakai `Path(__file__).resolve().parents[1]`).

---

# Keputusan yang diambil, dan alasannya

## D1. Sumber data: unduh 4H langsung, bukan resample dari arsip lokal

Ada dua sumber lokal yang tergoda untuk dipakai:

| Lokasi | Isi | Kenapa tidak dipakai |
|---|---|---|
| `C:\Crypto data 2\data\raw\klines\` | perp futures **1H**, 810 simbol, Jun 2024 – Ags 2026 | Timeframe salah (harus diresample = satu lapis asumsi) dan periodenya tidak menutup Jan 2024 – Sep 2026 |
| `C:\Crypto data\crypto-v1.2-data\`, `v1.3\data\` | **spot**, **harian**, mulai 2019 | Instrumen dan timeframe dua-duanya salah |

Keputusan Dew: unduh bar 4H asli dari `data.binance.vision/data/futures/um/`.
Tidak ada resampling sama sekali di project ini. Tiap file diverifikasi SHA256
terhadap `.CHECKSUM` yang diterbitkan Binance.

Arsip lokal 1H **tetap dipakai** untuk satu hal: memeringkat likuiditas saat
menyeleksi universe (`experiments/p2_universe.py:56`). Itu satu-satunya path
absolut ke folder luar di seluruh kode.

## D2. Periode: Jan 2024 – 19 Sep 2026

Bulan penuh dari arsip monthly s/d Ags 2026, plus file daily 1–19 Sep 2026
(arsip bulanan September belum terbit — hari kerja project ini 20 Sep).

## D3. Universe: ikut brief, terima survivorship bias

Brief §6.1 hanya bilang "likuiditas tertinggi". Arsip Binance sebenarnya
**memuat koin delisted** — terverifikasi: MATIC, FTT, SRM, OCEAN, AGIX, RAY, BNX
semuanya ada. Jadi bias ini **bisa** dihindari.

Dew memilih ikut brief. Konsekuensinya dicatat besar di report: syarat
"data lengkap sepanjang periode" otomatis membuang koin yang mati di tengah
jalan, dan arahnya membuat hasil **terlalu optimis**.

Ukuran kasar churn-nya: dari 810 simbol di arsip lokal, hanya **277** yang punya
data di ketiga bulan contoh (Jul 2024, Jul 2025, Jul 2026).

## D4. Sizing: risiko tetap 1% equity AWAL, tidak di-compound

Brief §3.5. Alasannya: yang diukur kualitas sinyal, bukan efek compounding.
Akibatnya R bisa dijumlahkan linear dan max DD dalam R punya arti.

Pine aslinya memakai `percent_of_equity 20%` dengan `initial_capital 50.000`.
Sizing tidak mempengaruhi jumlah trade maupun win rate, jadi perbandingan
replikasi tetap sah untuk dua angka itu.

## D5. `tickSize` diturunkan, bukan diambil dari exchange

`fapi.binance.com` tidak reachable dari mesin ini (diprobe 2026-09-20: timeout),
jadi `exchangeInfo` tidak bisa diambil. `tickSize` diturunkan dari jumlah desimal
terbanyak di kolom harga, dibaca sebagai **teks mentah** dari CSV — bukan dari
float, karena float sudah tidak eksak.

ETHUSDT: 2 desimal konsisten di 51/51 file → tickSize 0,01.

**Status: asumsi, tidak bisa diadu dengan nilai resmi.** Trik sejenis untuk
`stepSize` pernah cocok 54/54 di project lain, tapi itu stepSize, bukan tickSize.

## D6. Warm-up data untuk indikator (Fase 4 dan seterusnya)

Percentile rank VixFix butuh 500 bar riwayat. Tanpa itu, 51 dari 515 sinyal
(9,9%) kehilangan nilainya — padahal brief §8.2 mewajibkan **semua** sinyal ikut.

Solusi: unduh arsip Agustus–Desember 2023 khusus untuk mengisi jendela lookback.
Data 2023 **tidak pernah** dipakai sebagai periode uji — nol sinyal diambil dari
sana, nol trade dihitung di sana.

Efek samping yang harus diketahui: script `p7_versi_forward.py` juga memakai
warm-up, sehingga beberapa sinyal awal yang di Fase 1–5 terbuang (ATR/RSI belum
terbentuk) kini ikut masuk. Bedanya kecil — **503 vs 499 trade, expectancy
+0,1855 vs +0,1903 R**. Versi ber-warm-up lebih benar; kesimpulan tidak berubah.

## D7. Mode intrabar ketiga (`tv_emulator`) ditambahkan untuk replikasi saja

Pine memakai `strategy.exit(stop=..., limit=...)`. Kalau satu bar menyentuh
keduanya, TradingView tidak memakai asumsi pesimis — broker emulator-nya menebak
jalur intrabar dari arah bar. Tanpa mode ini, "jumlah trade beda" tidak bisa
dipisahkan antara bug dan beda asumsi.

Mode ini **tidak pernah dipakai** di Fase 1 ke atas. Dan ternyata tidak perlu:
ambiguitas intrabar **0,0% di 1.927 trade**, jadi ketiga mode memberi hasil
identik persis.

---

# Insiden — hal yang sempat salah dan bagaimana ketahuan

## I1. Cek cakupan universe bolong — WIFUSDT lolos padahal tidak layak

**Masalah.** Seleksi universe memeriksa ketersediaan file arsip dengan HTTP HEAD.
WIFUSDT lolos karena file `2024-01` ada. Tapi isinya baru mulai **18 Januari 2024**
— WIF listing pertengahan bulan. Hasilnya 5.853 bar dari 5.958 yang seharusnya.

Validator `src/data.py` tidak menangkapnya karena ia memeriksa gap **di dalam**
rentang data yang ada; kalau datanya memang mulai belakangan, tidak ada gap.

**Ketahuan dari** kolom `bar=5853` di log, yang tidak cocok dengan 5958 milik koin
lain — padahal `lolos=True`.

**Perbaikan.** Tambah cek cakupan penuh di `p2_universe.py`:
`q.n_bars == n_penuh and q.first_bar == bar_awal and q.last_bar == bar_akhir`.
WIFUSDT ditolak, ENAUSDT juga ditolak (arsip 2024-01..03 hilang), BCHUSDT masuk
menggantikan.

**Penting:** perbaikan dilakukan **sebelum** satu hasil backtest pun dilihat, jadi
bukan seleksi yang didorong hasil.

## I2. Max drawdown dihitung dalam urutan simbol, bukan kronologis

**Masalah.** `p2b_funding.py` membangun daftar trade dengan iterasi per simbol,
lalu menghitung max drawdown langsung dari urutan itu. Kurva equity portofolio
harus mengikuti **waktu**, bukan abjad simbol.

**Gejalanya** drawdown turun dari 33,0 R (Fase 2) jadi 10,1 R tanpa alasan.

**Perbaikan.** `sort_values("entry_time")` sebelum menghitung. Setelah diperbaiki:
33,0 → 33,5 R, konsisten dengan Fase 2.

## I3. Ekspektasi test trailing salah, engine-nya benar

Test `test_trailing_tidak_lookahead` awalnya mengharapkan exit di harga 135
(level trail dari bar sebelumnya). Engine mengembalikan 95.

Engine yang benar: bar itu **buka** di 95, jauh di bawah trail 135. Stop tidak
bisa terisi di harga yang tidak pernah diperdagangkan (asumsi F).

**Yang muncul dari sini** adalah batasan model yang layak dicatat: aturan "exit
dibenarkan oleh trail bar sebelumnya" (wajib per brief §4) membuat bar yang
mencetak high tinggi lalu berbalik menaikkan trail ke level yang sudah tidak
berlaku. Arah biasnya **konservatif** — hasil trailing terlihat lebih buruk dari
kenyataan — jadi kesimpulan "trailing tidak membantu" mungkin sedikit terlalu
keras. Perilaku ini dikunci sebagai test tersendiri
(`test_trailing_aturan_bar_sebelumnya_punya_harga`).

## I4. Print diagnostik salah indeks pada cek toleransi

Saat menyusun contoh sinyal untuk report 07, print ad-hoc memakai `df.iloc[b+1]`
untuk mencari `close[i+1]` Pine. Yang benar `df.iloc[b-1]` — penomoran Pine
mundur, jadi `[i+1]` adalah bar yang **lebih lama**, yaitu index array lebih kecil.

**Kode produksi tidak terpengaruh** — `strategy.py` memakai `c[t - (i + 1)]` yang
sudah benar sejak awal, dan `test_toleransi_wobble_batas_persis` memverifikasinya
di batas persis. Yang salah hanya print sementara; contoh di report sudah dihitung
ulang.

## I5. Temuan palsu di Fase 4 yang nyaris masuk report

Uji rank correlation VixFix memberi **rho +0,1995, p = 0,000005**, positif di
**14 dari 15 koin**, median rho +0,192. Konsisten antar simbol, p sangat kecil.

**Yang menyelamatkan:** angka itu tidak cocok dengan tetangganya — Pearson di data
yang sama cuma +0,019 (p = 0,66). Dua ukuran tidak akan sejauh itu bedanya kalau
hubungannya nyata.

Ditelusuri, sumbernya:

| Korelasi VixFix dengan | rho | p |
|---|---:|---:|
| **Menang atau kalah** | **+0,006** | **0,90** |
| Jarak stop | +0,431 | 1e-24 |
| Biaya komisi dalam R | −0,425 | 6e-24 |

R di strategi ini berkumpul di dua titik (~−1,0 dan ~+1,5). Yang membedakan −1,01
dari −1,03 hanya **biaya**. VixFix tinggi → stop lebih lebar → posisi lebih kecil
per unit risiko → komisi dalam R lebih kecil. Seluruh "temuan" itu aritmetika
biaya transaksi.

Diagnostiknya sekarang jadi bagian tetap dari `p4_vixfix_bucket.py`, bukan
pemeriksaan sekali pakai.

## I6. Status `fapi.binance.com` berubah-ubah antar sesi

Catatan sesi 2026-09-07 menyatakan `fapi` merespons HTTP 200. Diprobe ulang
2026-09-20: **timeout**. Akibatnya `exchangeInfo`, `tickSize`, `stepSize`, dan
`MIN_NOTIONAL` semuanya jadi asumsi (lihat D5).

**Pelajaran: probe tiap sesi, jangan percaya catatan sesi mana pun soal ini.**
Memori pengguna sudah diperbarui.

## I7. SOL dan XRP dikeluarkan dari uji out-of-sample

Dua-duanya kehilangan **30 bar** di rentang yang identik: 26–28 Feb 2022 dan
1–2 Apr 2022. Rentang yang sama persis di dua koin menandakan lubang penerbitan
arsip Binance, bukan penghentian perdagangan.

Dikeluarkan sesuai brief §2.2 — tidak diinterpolasi diam-diam. Universe OOS jadi
8 koin, bukan 10. Memasukkannya kembali setelah melihat hasil = data dredging,
jadi tidak dikerjakan.

---

# Penyimpangan dari brief, dan alasannya

| Penyimpangan | Alasan | Disetujui? |
|---|---|---|
| **Python 3.14.5**, bukan 3.11 | 3.11 tidak terpasang di mesin ini | Ya, Dew: "pakai python 3.14 aja, gpp" |
| Mode intrabar `tv_emulator` ditambahkan | Supaya "jumlah trade beda" bisa dipisah antara bug dan beda asumsi (§5.1 meminta investigasi) | Dilaporkan sebelum dipakai; tidak dipakai di Fase 1+ |
| `p1b_stopwidth_control.py` — uji tandingan di luar brief | T13 versi brief punya pembanding yang tidak setara; tanpa uji ini kesimpulan Fase 1 bisa salah baca | Dilaporkan sebagai uji tambahan, hasil T13 asli tetap primer |
| `p2b_funding.py` — biaya funding | Diminta Dew | Ya |
| `p5b_ema200_drawdown.py` — uji permutasi drawdown | Diminta Dew; menutup satu butir "tidak diketahui" di Fase 5 | Ya |
| `p6_walkforward_oos.py` — uji out-of-sample | Diminta Dew; tidak ada di brief tapi paling menentukan | Ya |
| `p7_versi_forward.py` — tiga versi + modal $100 | Diminta Dew untuk forward test | Ya |
| Warm-up data 2023 dan 2020 | Supaya indikator terbentuk penuh dan tidak ada sinyal terbuang (brief §8.2 mewajibkan semua sinyal ikut) | Dilaporkan; efeknya diukur (503 vs 499 trade) |

**Yang TIDAK pernah dilakukan:** tidak ada parameter strategi yang diubah,
sekali pun, sepanjang project. Riwayat `config.yaml` di `CHANGELOG_CONFIG.md`
— dua entri, dua-duanya sebelum eksperimen dijalankan.

---

# Hal teknis yang mudah salah kalau ini diimplementasikan ulang

| Hal | Yang benar | Kalau salah |
|---|---|---|
| **Smoothing RSI/ATR** | **RMA (Wilder)**, bukan EMA. Seed = SMA dari n nilai pertama | Filter `rsi > 40` ada persis di wilayah sensitif. Ada test khusus yang merah kalau RMA diganti EMA |
| **Indeks toleransi** | `close[i] > close[i+1] × 0,9995` untuk i = 0..3 — `[i+1]` adalah bar yang **lebih lama** | Lihat insiden I4 |
| **Jumlah pasang toleransi** | **4**, bukan 5. Pasangan bar 4 vs bar 5 tidak pernah diperiksa | Pola sah akan tertolak |
| **`low[i] <= low[5]` = GAGAL** | Menyentuh sama persis sudah membatalkan | Sinyal palsu bertambah |
| **Harga fill** | Open bar N+1, bukan close bar N | Hasil tidak akan cocok dengan backtest |
| **Interval funding** | **Tidak seragam**: 1000BONK dan TIA tiap **4 jam**, 13 koin lain 8 jam | Biaya dua koin itu terhitung setengahnya |
| **Timestamp** | `open_time`, milidetik, **UTC**, = waktu **buka** bar | Semua sinyal geser |
| **Urutan kronologis** untuk max DD | Wajib `sort_values("entry_time")` sebelum hitung | Lihat insiden I2 |

---

# Yang masih tidak diketahui

1. **Apakah filter MA200 bertahan di periode ketiga.** Satu-satunya benang yang
   masih hidup. Memilihnya *karena* ia selamat di OOS = memakai OOS untuk
   memutuskan, yang mengubah OOS jadi in-sample. Butuh jendela baru yang belum
   pernah disentuh.
2. **Besarnya survivorship bias.** Universe dipilih pakai likuiditas 2024–2026.
   Untuk uji 2021–2023 itu berarti menguji koin yang sudah diketahui selamat.
   Arahnya **menguntungkan** strategi — dan ia tetap gagal.
3. **Apakah CI95 out-of-sample menutup kemungkinan edge kecil.** Rentangnya
   [−0,151 , +0,140] R. Dengan 273 trade, efek kecil tidak akan terdeteksi.
   "Tidak ada bukti" ≠ "terbukti tidak ada".
4. **Apakah struktur pasar berubah** antara 2021 dan 2025. Mungkin ada pola yang
   hanya ada di satu era — tapi strategi yang hanya jalan di satu era, dan kita
   tidak tahu era mana yang sedang berjalan, tidak bisa dipakai.
5. **Slippage sesungguhnya.** Asumsi 1 tick optimis untuk koin tipis, terutama
   saat stop tereksekusi di pasar bergerak cepat.
6. **Funding di rezim ekstrem.** 2024–2026 funding-nya jinak.
7. **`tickSize` dan `MIN_NOTIONAL`** berstatus asumsi — `fapi` tidak reachable.
8. **Kenapa BTC terburuk out-of-sample** (−0,272 R) padahal in-sample positif
   (+0,243 R). Belum diselidiki.
9. **Apakah posisi 117 hari bertahan di kenyataan.** Margin, leverage tier,
   delisting — nol pemodelan.
10. **Efek korelasi antar trade terhadap semua p-value.** Semua uji menganggap
    trade independen. Breadth efektif ~1,5, jadi p sebenarnya lebih besar —
    artinya hasil "tidak signifikan" **lebih kuat**, dan hasil "signifikan"
    lebih lemah.

---

# Cara menilai project ini

Yang harus diperiksa kalau ada yang mau membantah kesimpulannya:

| Klaim | Cara memverifikasi |
|---|---|
| Engine-nya benar | `python -m pytest tests/ -q` → 65 hijau. Termasuk parity Pine, anti-lookahead, akuntansi tertutup, determinisme |
| Terjemahan Pine-nya benar | `tests/test_strategy.py` — tiap syarat Pine punya test batas tersendiri. Plus replikasi TradingView meleset 2,3% |
| Datanya benar | SHA256 tiap file diverifikasi terhadap `.CHECKSUM` Binance. `results/00_data_quality*.md` |
| Angkanya bisa direproduksi | Semua seed dikunci (20260920). Jalankan dua kali → bit-identik |
| Tidak ada tuning | `CHANGELOG_CONFIG.md` — dua entri, dua-duanya sebelum eksperimen |
| Kesimpulannya jujur | Tiap report punya bagian "yang belum kita tahu" yang tidak boleh kosong, dan conviction score dengan alasan spesifik |

## Menjalankan ulang seluruhnya

```bash
python -m pip install -r requirements.txt
python -m pytest tests/ -q

python experiments/00_data_inventory.py
python experiments/00_replication_eth.py
python experiments/p1_t13_random.py           # ~3 menit
python experiments/p1b_stopwidth_control.py
python experiments/p2_universe.py             # ~15 menit (HEAD + unduh)
python experiments/p2_pooled.py
python experiments/p2_pooled.py --with-short
python experiments/p2b_funding.py
python experiments/p3_exit_surgery.py
python experiments/p4_vixfix_bucket.py
python experiments/p5_regime_ablation.py
python experiments/p5b_ema200_drawdown.py
python experiments/p6_walkforward_oos.py      # ~20 menit (unduh 2020-2023)
python experiments/p7_versi_forward.py
```

## Peta dokumen

| File | Isi |
|---|---|
| `Sequence Snap Report Trading Strategy.md` | **Mulai dari sini** — dokumen utama: aturan entry, tiga versi, modal $100 |
| `reports/01` … `06` | Satu report per fase — metode dan keberatan tiap uji |
| `PROJECT_LOG_Sequence-Snap.md` | **Dokumen ini** — keputusan, insiden, penyimpangan |
| `CHANGELOG_CONFIG.md` | Riwayat perubahan parameter |
| `results/` | Output mentah: json + csv, satu per eksperimen |

---

# Penilaian akhir

Dua pertanyaan berbeda pantas dapat dua jawaban berbeda:

| Pertanyaan | Keyakinan |
|---|---|
| Apakah entry Sequence Snap punya *sedikit* edge di atas entry acak? | **~55%** |
| Apakah konfigurasi apa pun dari strategi ini layak dipakai dengan uang? | **~10%** |

Strategi ini mengalahkan entry acak di persentil 100, dan tetap di 99,9 setelah
lebar stop disetarakan. Bagian itu selamat dari setiap serangan.

Tapi expectancy out-of-sample runtuh dari +0,190 R jadi **−0,005 R**, kalah
signifikan di bear market 2022 (t = −2,69), dan penjelasan rezim yang dibangun
sepanjang lima fase juga tidak bereplikasi — nol di bull maupun bear.

**Yang dihasilkan project ini bukan strategi yang menghasilkan uang, melainkan
kepastian bahwa strategi ini tidak akan menghabiskan uang — dan kerangka kerja
yang bisa menguji kandidat berikutnya jauh lebih cepat.**
