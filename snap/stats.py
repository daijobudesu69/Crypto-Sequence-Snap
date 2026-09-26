"""Ringkasan forward test dari state/trades.csv, termasuk aturan berhenti.

Aturan berhenti disepakati SEBELUM trade pertama (Report 10.3, setup §6).
Bot hanya MEMERIKSA dan MENGUMUMKAN -- bot tidak menghentikan dirinya sendiri,
karena keputusan berhenti adalah keputusan manusia, dan forward test yang
berhenti diam-diam tidak bisa dibedakan dari yang rusak.
"""
from . import compat  # noqa: F401
import math

MAX_DRAWDOWN_PCT = -20.0
MAX_LOSING_STREAK = 15
MIN_TRADES_FOR_VERDICT = 100

# Acuan historis Versi 2 (Report 5.1 / 7.3). Versi 3 = V2 di data 2021-2023.
REF_V2_EXPECTANCY_R = 0.2584
REF_V3_EXPECTANCY_R = 0.1915
REF_LONGEST_STREAK = 12


def _num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def summarize(trades: list[dict], capital: float) -> dict:
    """Trade diurutkan menurut waktu exit sebelum dihitung.

    Kurva equity harus kronologis, bukan urutan baris -- PROJECT_LOG insiden I2:
    max drawdown yang dihitung dalam urutan simbol turun dari 33 R jadi 10 R.
    """
    rows = sorted(trades, key=lambda r: str(r.get("waktu_exit_utc") or ""))
    rs, pnls = [], []
    for r in rows:
        R = _num(r.get("R_realisasi"))
        if R is None:
            continue
        rs.append(R)
        pnls.append(_num(r.get("pnl_usd")) or 0.0)

    equity, peak, max_dd = capital, capital, 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        max_dd = min(max_dd, (equity / peak - 1) * 100 if peak else 0.0)
    cur_dd = (equity / peak - 1) * 100 if peak else 0.0

    streak = longest = 0
    for R in rs:
        streak = streak + 1 if R < 0 else 0
        longest = max(longest, streak)

    n = len(rs)
    wins = sum(1 for R in rs if R > 0)
    out = {
        "n": n, "sum_R": sum(rs), "expectancy_R": (sum(rs) / n) if n else 0.0,
        "win_rate": (wins / n * 100) if n else 0.0,
        "pnl_usd": sum(pnls), "equity_usd": equity,
        "drawdown_pct": cur_dd, "max_drawdown_pct": max_dd,
        "losing_streak": streak, "longest_losing_streak": longest,
    }
    out["stop_rules"] = stop_rules(out)
    return out


def stop_rules(s: dict) -> list[str]:
    hit = []
    if s["max_drawdown_pct"] <= MAX_DRAWDOWN_PCT:
        hit.append(f"drawdown paper {s['max_drawdown_pct']:.1f}% menembus "
                   f"{MAX_DRAWDOWN_PCT:.0f}% -- berhenti, evaluasi ulang")
    if s["longest_losing_streak"] >= MAX_LOSING_STREAK:
        hit.append(f"{s['longest_losing_streak']} kekalahan beruntun "
                   f"(batas {MAX_LOSING_STREAK}, rekor historis {REF_LONGEST_STREAK})")
    if s["n"] >= MIN_TRADES_FOR_VERDICT and s["expectancy_R"] <= 0:
        hit.append(f"{s['n']} trade, expectancy {s['expectancy_R']:+.3f} R <= 0 "
                   "-- strategi ditolak untuk watchlist ini")
    return hit
