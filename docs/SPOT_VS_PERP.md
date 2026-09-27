# Sumber data per koin — kedekatan dengan Binance futures

Diukur 2026-09-27 01:42 UTC oleh `tools/measure_spot_vs_perp.py`. Acuan: arsip resmi Binance USD-M perp (data.binance.vision), 2024-01 .. 2026-08. Sinyal dibandingkan sejak 2024-07-01 atau 1000 bar setelah data sumber mulai (pemanasan EMA200), mana yang lebih akhir.

## 1. Replikasi contoh Report Bagian 3 (ETHUSDT perp, Versi 1)

| | Report | Repo ini |
|---|---:|---:|
| Sinyal 2024-09-09 08:00 UTC | ada | ada |
| RSI bar 0 / bar 1 | 48,52 / 48,33 | 48.52 / 48.33 |
| Stop / target | 2238,88 / 2426,93 | 2238.88 / 2426.93 |

**Hasil: COCOK**

## 2. Kedekatan tiap sumber dengan Binance futures

| Koin | Sumber | Beda close | Beda close 90 hr | Beda high/low | Sinyal perp | Cocok | Hilang | Palsu | **Kecocokan** | Trade | ΣR (sumber ini) | Dipilih |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| ETHUSDT | spot Binance | 0.046% | 0.047% | 0.046% | 23 | 21 | 2 | 1 | **87.5%** | 21 | +13.46 | ✅ |
| ETHUSDT | Gate perp | 0.009% | 0.006% | 0.015% | 23 | 19 | 4 | 2 | **76.0%** | 20 | +12.01 |  |
| BNBUSDT | spot Binance | 0.046% | 0.056% | 0.047% | 28 | 24 | 4 | 1 | **82.8%** | 24 | +5.16 | ✅ |
| BNBUSDT | Gate perp | 0.072% | 0.109% | 0.071% | 28 | 23 | 5 | 4 | **71.9%** | 26 | +8.13 |  |
| XRPUSDT | spot Binance | 0.051% | 0.053% | 0.052% | 20 | 18 | 2 | 0 | **90.0%** | 18 | +9.19 | ✅ |
| XRPUSDT | Gate perp | 0.012% | 0.009% | 0.017% | 20 | 18 | 2 | 1 | **85.7%** | 19 | +8.16 |  |
| DOGEUSDT | spot Binance | 0.049% | 0.055% | 0.050% | 14 | 13 | 1 | 0 | **92.9%** | 13 | +6.84 |  |
| DOGEUSDT | Gate perp | 0.014% | 0.014% | 0.018% | 14 | 14 | 0 | 0 | **100.0%** | 14 | +5.83 | ✅ |
| AVAXUSDT | spot Binance | 0.056% | 0.062% | 0.058% | 10 | 8 | 2 | 2 | **66.7%** | 10 | +4.86 |  |
| AVAXUSDT | Gate perp | 0.031% | 0.015% | 0.030% | 10 | 9 | 1 | 0 | **90.0%** | 9 | +0.91 | ✅ |
| TRXUSDT | spot Binance | 0.054% | 0.061% | 0.056% | 39 | 25 | 14 | 5 | **56.8%** | 30 | +6.44 |  |
| TRXUSDT | Gate perp | 0.025% | 0.021% | 0.025% | 39 | 30 | 9 | 6 | **66.7%** | 36 | -0.09 | ✅ |
| XMRUSDT | spot Binance | nan% | nan% | nan% | 21 | 0 | 21 | 0 | **0.0%** | 0 | +0.00 |  |
| XMRUSDT | Gate perp | 0.141% | 0.048% | 0.134% | 21 | 9 | 12 | 3 | **37.5%** | 11 | +6.21 | ✅ |
| NEARUSDT | spot Binance | 0.064% | 0.061% | 0.066% | 14 | 12 | 2 | 0 | **85.7%** | 12 | +5.35 |  |
| NEARUSDT | Gate perp | 0.042% | 0.031% | 0.043% | 14 | 13 | 1 | 0 | **92.9%** | 12 | +2.91 | ✅ |
| TAOUSDT | spot Binance | 0.053% | 0.061% | 0.057% | 11 | 5 | 6 | 2 | **38.5%** | 6 | +6.43 |  |
| TAOUSDT | Gate perp | 0.039% | 0.037% | 0.042% | 11 | 8 | 3 | 1 | **66.7%** | 8 | +6.79 | ✅ |

Kecocokan = cocok ÷ (sinyal perp + sinyal palsu): sinyal yang hilang DAN sinyal yang tidak pernah ada di backtest sama-sama dihitung sebagai meleset. Beda = median selisih absolut per bar terhadap Binance futures.

### Pilihan

```python
PRIMARY = {
    "ETHUSDT": "binance_spot_mirror",
    "BNBUSDT": "binance_spot_mirror",
    "XRPUSDT": "binance_spot_mirror",
    "DOGEUSDT": "gate_io_perp",
    "AVAXUSDT": "gate_io_perp",
    "TRXUSDT": "gate_io_perp",
    "XMRUSDT": "gate_io_perp",
    "NEARUSDT": "gate_io_perp",
    "TAOUSDT": "gate_io_perp",
}
```

## 3. Versi 2 di Binance futures, per koin (acuan kasar, BUKAN validasi)

| Koin | Sejak | Trade | Trade/bulan | Win rate | Expectancy | ΣR |
|---|---|---:|---:|---:|---:|---:|
| ETHUSDT | 2024-07-01 | 22 | 0.85 | 68% | +0.679 R | +14.94 |
| BNBUSDT | 2024-07-01 | 27 | 1.04 | 59% | +0.443 R | +11.95 |
| XRPUSDT | 2024-07-01 | 20 | 0.77 | 60% | +0.484 R | +9.67 |
| DOGEUSDT | 2024-07-01 | 14 | 0.54 | 57% | +0.416 R | +5.83 |
| AVAXUSDT | 2024-07-01 | 10 | 0.38 | 50% | +0.238 R | +2.38 |
| TRXUSDT | 2024-07-01 | 39 | 1.50 | 49% | +0.173 R | +6.76 |
| XMRUSDT | 2024-07-01 | 20 | 0.77 | 45% | +0.103 R | +2.07 |
| NEARUSDT | 2024-07-01 | 13 | 0.50 | 54% | +0.335 R | +4.35 |
| TAOUSDT | 2024-09-25 | 10 | 0.43 | 70% | +0.733 R | +7.33 |

Periode ini tumpang tindih dengan periode yang dipakai membangun strategi (2024–2026), jadi angkanya batas atas yang optimis. TRX, XMR, NEAR, TAO ditambahkan setelah riset; angka mereka di sini **tidak boleh** dipakai untuk memilih atau membuang koin — itu data snooping.

## 4. Cek jumlah trade Versi 1 vs setup V1 (perp, 2024-01..2026-08)

| Koin | Repo ini | Setup V1 (s/d 19 Sep 2026) |
|---|---:|---:|
| ETHUSDT | 43 | 43 |
| BNBUSDT | 41 | 42 |
| XRPUSDT | 39 | 39 |
| DOGEUSDT | 37 | 37 |
| AVAXUSDT | 25 | 25 |

Boleh sedikit di bawah angka setup (September 2026 tidak ikut).

