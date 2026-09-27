"""Tab `ringkasan` di Google Sheets + sinkron penuh CSV -> Sheets.

Tab ringkasan menjawab dalam sekali lihat semua yang dibutuhkan untuk menilai
forward test (setup §6-7): progres ke 100 trade, expectancy dan win rate
dibanding acuan Versi 3, drawdown dan kalah beruntun dibanding batas berhenti,
dan hasil per koin. Ditulis ulang utuh setiap kali, jadi tidak pernah basi
sebagian.
"""
from . import compat  # noqa: F401
import pandas as pd

from . import datafeed, ledger, sheets, stats
from .config import ENGINE_VERSION

STARTED = {"ETHUSDT": "2026-09-26", "BNBUSDT": "2026-09-26", "XRPUSDT": "2026-09-26",
           "DOGEUSDT": "2026-09-26", "AVAXUSDT": "2026-09-26", "NEARUSDT": "2026-09-27"}


def _r(x, n=3):
    return None if x is None else round(float(x), n)


def summary_rows(cfg: dict, st: dict) -> list[list]:
    trades = ledger.read_rows(ledger.TRADES)
    events = ledger.read_rows(ledger.EVENTS)
    s = stats.summarize(trades, cfg["paper"]["capital_usd"])
    rules = s["stop_rules"]
    now = pd.Timestamp.now(tz="UTC")
    n_sig = sum(1 for e in events if e.get("event") == "SIGNAL")

    def ok(flag):
        return "TERPICU" if flag else "aman"

    rows = [
        ["Sequence Snap v2 — forward test (paper trading)", ""],
        ["diperbarui (UTC)", now.strftime("%Y-%m-%d %H:%M")],
        ["versi mesin", ENGINE_VERSION],
        [],
        ["SETUP", ""],
        ["mulai", "2026-09-26 (NEAR sejak 2026-09-27)"],
        ["watchlist", ", ".join(s_.replace("USDT", "") for s_ in datafeed.SYMBOLS)],
        ["timeframe", "4H — sinyal di close, entry di open lilin berikutnya"],
        ["modal kertas (USD)", cfg["paper"]["capital_usd"]],
        ["risiko per trade", f"{cfg['paper']['risk_pct']}% modal awal = "
                             f"${cfg['paper']['capital_usd'] * cfg['paper']['risk_pct'] / 100:.2f}"],
        ["komisi per sisi", f"{cfg['paper']['commission_pct']}%"],
        ["tidak dimodelkan", "slippage & funding (isi manual di tab trades bila eksekusi sungguhan)"],
        [],
        ["PROGRES", ""],
        ["sinyal tercatat", n_sig],
        ["trade selesai", s["n"]],
        ["progres ke 100 trade", f"{s['n']}/100"],
        ["posisi terbuka", len([1 for v in (st.get("symbols") or {}).values()
                                 if v.get("position")])],
        [],
        ["HASIL", "nilai", "acuan V3 (out-of-sample)", "acuan V2 (in-sample, batas atas)"],
        ["expectancy (R/trade, bersih komisi)", _r(s["expectancy_R"]), 0.1915, 0.2584],
        ["win rate (%)", _r(s["win_rate"], 1), 49.4, 51.7],
        ["total R", _r(s["sum_R"], 2), "", ""],
        ["PnL paper (USD)", _r(s["pnl_usd"], 2), "", ""],
        ["equity paper (USD)", _r(s["equity_usd"], 2), "", ""],
        [],
        ["RISIKO", "nilai", "batas berhenti", "status"],
        ["drawdown sekarang (%)", _r(s["drawdown_pct"], 2), -20, ""],
        ["drawdown terdalam (%)", _r(s["max_drawdown_pct"], 2), -20,
         ok(s["max_drawdown_pct"] <= stats.MAX_DRAWDOWN_PCT)],
        ["kalah beruntun sekarang", s["losing_streak"], 15, ""],
        ["kalah beruntun terpanjang", s["longest_losing_streak"], 15,
         ok(s["longest_losing_streak"] >= stats.MAX_LOSING_STREAK)],
        ["expectancy setelah 100 trade", _r(s["expectancy_R"]) if s["n"] >= 100 else "belum 100 trade",
         "> 0", ok(s["n"] >= 100 and s["expectancy_R"] <= 0)],
        ["ATURAN BERHENTI", "TERPICU: " + " | ".join(rules) if rules else "tidak ada yang terpicu"],
        [],
        ["PER KOIN", "sumber data", "trade", "win", "total R", "expectancy R", "posisi terbuka", "mulai"],
    ]
    slots = st.get("symbols") or {}
    for sym in datafeed.SYMBOLS:
        rs = [float(t["R_realisasi"]) for t in trades
              if t.get("koin") == sym and t.get("R_realisasi") not in (None, "")]
        pos = (slots.get(sym) or {}).get("position")
        rows.append([sym, datafeed.PRIMARY[sym], len(rs), sum(1 for r in rs if r > 0),
                     _r(sum(rs), 2), _r(sum(rs) / len(rs)) if rs else "",
                     (f"entry {pos['entry_price']} · stop {pos['stop']} · target {pos['target']}"
                      if pos else "-"), STARTED.get(sym, "")])
    rows += [[], ["Sumber data: CSV di repo (state/) adalah catatan resmi; spreadsheet ini cerminnya."]]
    width = max(len(r) for r in rows)
    return [r + [""] * (width - len(r)) for r in rows]


def sync_all(cfg: dict, st: dict) -> dict:
    """Sinkron events/trades/runs dari CSV + tulis ulang ringkasan. Tidak pernah raise."""
    out = {}
    if not sheets.configured():
        return {"configured": False}
    for tab, path, cols in (("events", ledger.EVENTS, ledger.EVENT_COLS),
                            ("trades", ledger.TRADES, ledger.TRADE_COLS),
                            ("runs", ledger.RUNS, ledger.RUN_COLS)):
        out[tab] = sheets.sync(tab, cols, ledger.read_history(path))
    try:
        out["ringkasan"] = sheets.replace("ringkasan", summary_rows(cfg, st))
    except Exception as e:  # noqa: BLE001
        print(f"[report] ringkasan gagal: {type(e).__name__}: {e}")
        out["ringkasan"] = False
    return out
