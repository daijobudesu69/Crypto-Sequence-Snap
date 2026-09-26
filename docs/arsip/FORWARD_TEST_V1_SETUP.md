# Setup Forward Test — Sequence Snap Versi 1

**Versi:** 1 (indikator saja — pattern + RSI, **TANPA MA200**)
**Watchlist:** ETHUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, AVAXUSDT (perp Binance USDⓈ-M, 4H)
**Disiapkan:** 20 September 2026

> Versi 1 dipilih Dew karena persentase return lebih tinggi (+21,0%/tahun di modal
> $300 vs +16,1% Versi 2). Yang harus diingat sebelum mulai: Versi 1 adalah versi
> yang **gagal** di uji out-of-sample 2021-2023 (t = -0,07, nol). Versi 2 (+MA200)
> adalah satu-satunya yang bertahan di data yang belum pernah dilihat. Forward
> test ini pada dasarnya adalah **ujian ketiga** untuk Versi 1 — di data yang
> juga belum pernah dilihat (masa depan, bukan 2021-2023). Baca ini sebagai
> eksperimen terbuka, bukan strategi yang sudah terbukti.

---

## 1. Checklist sebelum mulai

- [ ] Baca `Sequence Snap Report Trading Strategy.md` Bagian 2 (syarat entry) dan Bagian 10 (rekomendasi)
- [ ] Tempel `pine/SequenceSnap_v1.pine` ke Pine Editor TradingView, compile, tidak ada error
- [ ] Pasang di **5 chart terpisah**, satu per koin, timeframe **4H**
- [ ] Pasang alert di tiap chart (lihat §3)
- [ ] Siapkan modal (Dew sudah konfirmasi $500 aman kalau forward test terbukti
      profit — lihat §2, ini di atas ambang $300 yang dibutuhkan)
- [ ] Siapkan `forward_test_log.csv` (disediakan, §5) untuk mencatat tiap trade
- [ ] Tulis tanggal mulai di log — dipakai untuk menghitung semua metrik nanti
- [ ] Sepakati aturan berhenti di §6 SEBELUM trade pertama, bukan sesudah

---

## 2. Modal — $500 dikonfirmasi aman, $300 adalah ambang minimum

Dew sudah menyatakan $500 bukan masalah kalau forward test terbukti profit.
Modal ditentukan belakangan, tapi catatan ini disiapkan sebagai acuan: **$500
sudah di atas ambang $300** di mana seluruh 186 sinyal historis (5 koin) bisa
dieksekusi tanpa tertolak MIN_NOTIONAL — jadi tidak ada hambatan teknis di
angka ini.

Proyeksi $500 berdasarkan data historis 2024-2026 (5 koin, Versi 1):

| | |
|---|---|
| 1 tahun (tanpa compounding) | **$604,95** (+21,0%) |
| Rentang 95% per tahun | $543,66 – $666,24 |
| 2,72 tahun penuh | $785,33 (+57,1%) |
| **Drawdown terdalam** | **$82,85 (16,6% modal)** |
| CAGR (dengan compounding) | +22,2% |
| Nilai 1 R (risiko per trade) | $5,00 |

**Ingat konteksnya:** ini proyeksi in-sample. Rentang 95% di atas mengabaikan
korelasi antar trade (breadth efektif watchlist ini belum diukur terpisah dari
15-koin penuh), jadi kemungkinan sebenarnya lebih lebar dari yang tertulis.

### Kenapa modal minimal $300 (bukan lebih rendah)

Dengan risiko 1% per trade, ukuran posisi ditentukan oleh jarak stop. Untuk ETH
(stop rata-rata ~5-6% dari harga), posisi di modal $100 sering di bawah minimum
order Binance ($20 untuk ETH).

Diuji di data historis 2024-2026, berapa sinyal yang benar-benar bisa dieksekusi
per level modal:

| Modal | ETHUSDT | BNBUSDT | XRPUSDT | DOGEUSDT | AVAXUSDT | Total |
|---|---:|---:|---:|---:|---:|---:|
| $100 | 20/43 | 41/42 | 38/39 | 35/37 | 25/25 | **159/186 (85%)** |
| $150 | 35/43 | 42/42 | 39/39 | 37/37 | 25/25 | 178/186 (96%) |
| $200 | 42/43 | 42/42 | 39/39 | 37/37 | 25/25 | 185/186 (99%) |
| **$300** | **43/43** | 42/42 | 39/39 | 37/37 | 25/25 | **186/186 (100%)** |

**ETH adalah satu-satunya yang bermasalah** di modal kecil — 23 dari 27 sinyal
yang tertolak di seluruh watchlist berasal dari ETH saja. Kalau Dew memang
modalnya di bawah $300, opsinya:
- naikkan risiko per trade khusus untuk sinyal ETH yang kena tolak (TIDAK
  disarankan — mengubah metodologi di tengah jalan), atau
- terima bahwa sebagian sinyal ETH terlewat (tulis di log sebagai
  `dilewati_min_notional`, JANGAN dihapus dari catatan), atau
- pakai modal $300 dari awal.

---

## 3. Setup Pine Script per koin

### 3.1 Input yang WAJIB sama di kelima chart

| Input | Nilai |
|---|---|
| Candles In The Run | 5 |
| Wobble Allowance (%) | 0.05 |
| Require RSI Agreement | **ON** |
| RSI Length | 14 |
| RSI Floor For Longs | 40 |
| Reward Target | 1.5R |
| Allow Longs | **ON** |
| Allow Shorts | **OFF** — jangan diubah |
| Size By Risk | **ON** |
| Risk Per Trade (%) | 1.0 |

File `pine/SequenceSnap_v1.pine` sudah mengunci ini sebagai default. Jangan ubah
apa pun di luar `initial_capital` (sesuaikan ke modal simulasi Dew) dan visual.

### 3.2 Memasang alert

Untuk tiap chart (ETHUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, AVAXUSDT):

1. Klik kanan chart → **Add Alert**
2. Condition: pilih script **"Sequence Snap v1 | Pattern Only (no MA200)"** →
   kondisi **"Sequence Snap v1 — LONG setup"**
3. Trigger: **Once Per Bar Close** (bukan "Once Per Bar" — sinyal harus dihitung
   di CLOSE bar, sesuai aturan §2 di dokumen utama)
4. Expiration: sesuaikan durasi forward test (misal 12 bulan)
5. Notifikasi: aktifkan yang paling cepat sampai ke Dew (App/Push disarankan,
   karena entry harus di open bar berikutnya — jeda 4 jam kalau pakai email)
6. Message: biarkan default. Alert-nya sudah menyertakan close, stop, target,
   dan % risiko otomatis — lihat contoh di §3.3.

### 3.3 Contoh isi alert yang akan diterima

```
SEQUENCE SNAP v1 (NO MA200) LONG | ETHUSDT | close 2314.10 | stop 2238.88
| target 2426.93 | risk 3.25% | ENTRY di OPEN lilin berikutnya
```

Saat alert ini masuk, tindakannya:
1. Tunggu lilin 4H berikutnya **dibuka** (bukan langsung eksekusi saat alert masuk)
2. Entry market order di harga open lilin itu
3. Pasang stop-loss di harga `stop` dari alert
4. Pasang take-profit di harga `target` dari alert
5. Hitung qty: `(modal x 1%) ÷ (harga entry aktual − stop)`

---

## 4. Ekspektasi frekuensi sinyal (dari data historis, bukan jaminan)

| Koin | Sinyal/bulan | Trade/tahun (perkiraan) |
|---|---:|---:|
| ETHUSDT | 1,32 | ~16 |
| BNBUSDT | 1,29 | ~15 |
| XRPUSDT | 1,20 | ~14 |
| DOGEUSDT | 1,14 | ~14 |
| AVAXUSDT | 0,77 | ~9 |
| **Gabungan** | **5,71** | **~69** |

Rata-rata **~1 sinyal setiap 5-6 hari** dari kelima koin gabungan. Sebarannya
tidak rata — historisnya berkisar 1 sampai 11 sinyal dalam sebulan, dan pernah
ada 1 bulan penuh tanpa sinyal sama sekali dari kelimanya.

Untuk sampel 100 trade (ambang minimal sebelum expectancy berarti apa-apa),
perkirakan **~18 bulan** forward test.

---

## 5. Log trade — kolom wajib

File `forward_test_log.csv` (disediakan kosong, siap diisi) punya kolom:

| Kolom | Cara isi |
|---|---|
| `no` | urut |
| `koin` | ETHUSDT / BNBUSDT / XRPUSDT / DOGEUSDT / AVAXUSDT |
| `waktu_sinyal_utc` | waktu close bar 0 (dari alert) |
| `waktu_entry_utc` | waktu open bar berikutnya (harus = waktu_sinyal + 4 jam) |
| `close_bar0` | harga dari alert |
| `low_bar5` | = level stop dari alert |
| `rsi_bar0` / `rsi_bar1` | untuk verifikasi manual filter RSI |
| `stop_rencana` | dari alert |
| `target_rencana` | dari alert |
| `harga_entry_aktual` | harga fill sungguhan (BUKAN close_bar0) |
| `qty` | ukuran posisi sungguhan |
| `notional` | qty × harga_entry_aktual |
| `dilewati_min_notional` | TRUE kalau notional < minimum Binance koin itu |
| `harga_exit_aktual` | |
| `alasan_exit` | stop / target / manual |
| `waktu_exit_utc` | |
| `bar_ditahan` | jumlah bar 4H dari entry ke exit |
| `slippage_entry_tick` | (harga_entry_aktual − close_bar0) dalam tick |
| `slippage_exit_tick` | |
| `funding_dibayar_usd` | jumlahkan dari histori funding exchange selama posisi terbuka |
| `pnl_usd` | hasil bersih setelah komisi dan funding |
| `R_realisasi` | pnl_usd ÷ (modal saat entry × 1%) |
| `catatan` | apa pun yang tidak biasa |

**Kenapa mencatat slippage dan funding secara terpisah:** backtest mengasumsikan
1 tick slippage dan funding rata-rata +0,012 R per trade. Kalau kenyataan jauh
beda, itu sinyal untuk menghitung ulang seluruh proyeksi — bukan sekadar detail.

---

## 6. Aturan berhenti — sepakati SEKARANG

| Kondisi | Tindakan |
|---|---|
| Drawdown modal simulasi menembus **−20%** | Berhenti, evaluasi ulang sebelum lanjut |
| **15 kekalahan beruntun** | Berhenti (rekor historis watchlist ini: 12, di 5-koin V1) |
| Setelah **100 trade**, expectancy gabungan masih ≤ 0 | Strategi ditolak untuk watchlist ini |
| Slippage nyata rata-rata **> 3× asumsi** (nyata > 3 tick) | Hitung ulang semua proyeksi biaya |
| Ada sinyal live yang **tidak cocok** dengan aturan §2 dokumen utama | Hentikan sementara, cari sebabnya sebelum lanjut |
| ETH kena tolak MIN_NOTIONAL berkali-kali dan modal tetap < $300 | Naikkan modal simulasi atau terima bias yang tercipta |

---

## 7. Yang harus diingat sepanjang forward test

1. **Ini bukan strategi yang terbukti.** Conviction keseluruhan 20%. Versi 1
   spesifik adalah yang gagal di satu-satunya uji out-of-sample yang sudah
   dikerjakan (2021-2023, t = -0,07).
2. **Bandingkan progress forward test dengan angka historis secara berkala**
   (tiap 20-25 trade): expectancy +0,307 R, win rate 53,8%, adalah acuan
   in-sample — kalau forward test jauh di bawah itu secara konsisten, itu
   informasi, bukan kebetulan yang harus diabaikan.
3. **Jangan menambah filter di tengah jalan** karena "kelihatannya membantu".
   Itu persis kesalahan yang brief riset ini larang keras (lihat §11 aturan
   yang dilarang di laporan utama).
4. **Tulis kegagalan sejelas keberhasilan.** Kalau forward test-nya juga gagal
   seperti Versi 1 di 2021-2023, itu hasil yang valid dan berharga — bukan
   kegagalan proses forward test-nya.

---

## Lampiran

| File | Isi |
|---|---|
| `pine/SequenceSnap_v1.pine` | Script yang dipasang di 5 chart |
| `forward_test_log.csv` | Template kosong untuk mencatat tiap trade |
| `Sequence Snap Report Trading Strategy.md` | Dokumen utama — semua bukti dan konteks |
| `PROJECT_LOG_Sequence-Snap.md` | Jejak keputusan dan insiden riset |
