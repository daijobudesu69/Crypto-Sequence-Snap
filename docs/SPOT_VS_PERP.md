# Spot vs perp — tracking error sinyal Sequence Snap

Diukur 2026-09-26 19:33 UTC oleh `tools/measure_spot_vs_perp.py`. Arsip bulanan resmi data.binance.vision, 2024-01 .. 2026-08, dievaluasi sejak 2024-07-01 (sebelumnya pemanasan EMA200).

## 1. Replikasi contoh Report Bagian 3 (ETHUSDT perp, Versi 1)

| | Report | Repo ini |
|---|---:|---:|
| Sinyal 2024-09-09 08:00 UTC | ada | ada |
| RSI bar 0 | 48,52 | 48.52 |
| RSI bar 1 | 48,33 | 48.33 |
| Stop | 2238,88 | 2238.88 |
| Target | 2426,93 | 2426.93 |
| close vs EMA200 | — | -10.63% (DIBLOKIR filter V2) |

**Hasil: COCOK**

## 2. Sinyal Versi 2: spot (bot) vs perp (backtest)

| Koin | Sinyal perp | Sinyal spot | Cocok | Hilang di spot | Palsu di spot | Kecocokan | Beda close (median) | Trade perp | ΣR perp | Trade spot | ΣR spot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ETHUSDT | 23 | 22 | 21 | 2 | 1 | **91.3%** | 0.046% | 22 | +14.94 | 21 | +13.46 |
| BNBUSDT | 28 | 25 | 24 | 4 | 1 | **85.7%** | 0.048% | 27 | +11.95 | 24 | +5.16 |
| XRPUSDT | 20 | 18 | 18 | 2 | 0 | **90.0%** | 0.051% | 20 | +9.67 | 18 | +9.19 |
| DOGEUSDT | 14 | 13 | 13 | 1 | 0 | **92.9%** | 0.050% | 14 | +5.83 | 13 | +6.84 |
| AVAXUSDT | 10 | 10 | 8 | 2 | 2 | **80.0%** | 0.056% | 10 | +2.38 | 10 | +4.86 |

**Gabungan: 84/95 sinyal perp muncul juga di spot (88.4%).**

Kecocokan = sinyal perp yang juga muncul di spot. "Palsu di spot" = sinyal yang hanya ada di spot, jadi tidak pernah ada di backtest. ΣR = R bersih komisi dari mesin paper repo ini, tanpa funding.

## 3. Cek jumlah trade Versi 1 vs setup V1 (perp, 2024-01..2026-08)

| Koin | Repo ini | Setup V1 (s/d 19 Sep 2026) |
|---|---:|---:|
| ETHUSDT | 43 | 43 |
| BNBUSDT | 41 | 42 |
| XRPUSDT | 39 | 39 |
| DOGEUSDT | 37 | 37 |
| AVAXUSDT | 25 | 25 |

Repo ini boleh sedikit di bawah angka setup (September 2026 tidak ikut). Selisih besar berarti mesin repo ini tidak sama dengan mesin riset.

