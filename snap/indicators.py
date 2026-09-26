"""Pine-faithful indicators.

Pine seeds ta.ema and ta.rma with an SMA of the first `length` values and then
runs the recursion. ta.rsi is RMA (Wilder) based -- a plain rolling mean or
pandas.ewm will not reproduce TradingView, which is why every smoother here is
written out explicitly.

Disalin dari Crypto-MEX (mex/indicators.py), yang sudah diadu dengan TradingView.
Yang dipakai Sequence Snap hanya ema (MA200), sma (opsi MA200 SMA) dan rsi.
Filter `rsi > 40` ada persis di wilayah yang sensitif terhadap smoothing, jadi
RMA di sini tidak boleh diganti EMA -- tests/test_strategy.py menjaganya.
"""
from . import compat  # noqa: F401
import numpy as np


def sma(x, n):
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, np.nan)
    if len(x) < n:
        return out
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x, n):
    """Pine ta.ema: seed = SMA(n) at index n-1, then alpha = 2/(n+1)."""
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, np.nan)
    if len(x) < n:
        return out
    a = 2.0 / (n + 1.0)
    out[n - 1] = np.mean(x[:n])
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1.0 - a) * out[i - 1]
    return out


def rma(x, n):
    """Pine ta.rma (Wilder): seed = SMA(n) at index n-1, then alpha = 1/n."""
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, np.nan)
    if len(x) < n:
        return out
    a = 1.0 / n
    seed = x[:n]
    if np.isnan(seed).any():
        return out
    out[n - 1] = np.mean(seed)
    for i in range(n, len(x)):
        v = x[i]
        out[i] = a * (0.0 if np.isnan(v) else v) + (1.0 - a) * out[i - 1]
    return out


def rsi(close, n=14):
    """Pine ta.rsi: RMA of gains / RMA of losses."""
    close = np.asarray(close, float)
    d = np.diff(close, prepend=np.nan)
    up = np.where(np.isnan(d), np.nan, np.maximum(d, 0.0))
    dn = np.where(np.isnan(d), np.nan, np.maximum(-d, 0.0))
    up[0] = 0.0
    dn[0] = 0.0
    # Pine's rma over ta.change() starts accumulating from bar 1.
    ru = rma(up[1:], n)
    rd = rma(dn[1:], n)
    ru = np.insert(ru, 0, np.nan)
    rd = np.insert(rd, 0, np.nan)
    out = np.full(close.shape, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = ru / rd
        out = 100.0 - 100.0 / (1.0 + rs)
    out = np.where(rd == 0, 100.0, out)
    out = np.where(ru == 0, 0.0, out)
    out[np.isnan(ru) | np.isnan(rd)] = np.nan
    return out
