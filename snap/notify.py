"""Pengiriman Telegram. Diadaptasi dari Crypto-MEX (mex/notify.py).

Dua aturan:

  * Pesan hanya dikirim kalau memang ada kejadian. Run tanpa sinyal tidak
    mengirim apa pun -- berhari-hari sunyi itu normal (~1 sinyal tiap 3-6 hari).
  * Run tidak boleh gagal karena Telegram tidak terjangkau. CSV adalah catatan
    resmi; Telegram hanya kemudahan. Pesan yang gagal tetap di outbox dan
    dicoba ulang tiap run.

Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID sebagai repository secret. Selama
salah satunya kosong, pesan dicetak ke log job -- jadi seluruh pipa bisa diuji
sebelum bot Telegram ada.
"""
from . import compat  # noqa: F401
import datetime as _dt
import html
import math
import os

import requests

API = "https://api.telegram.org/bot{token}/sendMessage"
WIB = _dt.timezone(_dt.timedelta(hours=7))


def esc(x) -> str:
    """Telegram menolak SELURUH pesan (HTTP 400) kalau parse_mode=HTML menemukan
    tag yang tidak dikenalnya. Teks exception sering memuat < > &."""
    return html.escape(str(x), quote=False)


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
                and os.environ.get("TELEGRAM_CHAT_ID", "").strip())


def send(text: str) -> bool:
    """True kalau Telegram menerima pesan. Tidak pernah raise."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        print("[notify] Telegram belum dikonfigurasi -- pesan di bawah tidak dikirim\n")
        print(text)
        return False
    try:
        r = requests.post(
            API.format(token=token),
            json={"chat_id": chat, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=25,
        )
        if r.status_code >= 400:
            print(f"[notify] telegram HTTP {r.status_code}: {r.text[:300]}")
            return False
        return True
    except Exception as e:  # noqa: BLE001
        # Tipe saja, JANGAN pesannya: exception requests memuat URL lengkap, dan
        # URL itu memuat token bot. Repo ini publik, log job-nya juga.
        print(f"[notify] telegram gagal: {type(e).__name__}")
        return False


# --------------------------------------------------------------------------- #
# format angka dan waktu
# --------------------------------------------------------------------------- #
def f(x, n=None):
    """Angka untuk dibaca manusia. Presisi mengikuti besarnya harga.

    Dua desimal hanya benar untuk harga seperti ETH. Di DOGE (~0,1) MEX pernah
    mencetak stop dan target sebagai angka yang sama persis. Di bawah 10,
    presisi bertambah sesuai besarnya nilai; nol di belakang dibuang.
    """
    if x is None:
        return "-"
    v = float(x)
    if n is not None:
        return f"{v:,.{n}f}"
    a = abs(v)
    if a >= 10:
        dec = 2
    elif a >= 1:
        dec = 4
    elif a > 0:
        dec = min(12, max(6, 5 - int(math.floor(math.log10(a)))))
    else:
        dec = 2
    s = f"{v:,.{dec}f}"
    if "." in s:
        whole, _, frac = s.rstrip("0").partition(".")
        s = f"{whole}.{(frac + '00')[:2] if len(frac) < 2 else frac}"
    return s


def usd(x) -> str:
    """+$4.40 / -$3.09 -- tanda di depan simbol dolar."""
    v = float(x)
    return f"{'-' if v < 0 else '+'}${abs(v):,.2f}"


def wib(iso) -> str:
    """Timestamp UTC -> 'dd-mm-yyyy HH:MM WIB'."""
    t = _dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=_dt.timezone.utc)
    return t.astimezone(WIB).strftime("%d-%m-%Y %H:%M WIB")


def candle(iso) -> str:
    """Lilin 4H yang BUKA di `iso`: 'dd-mm-yyyy HH:MM–HH:MM WIB'."""
    a, b = wib(iso), wib(_plus4h(iso))
    return f"{a[:-4]}–{b[11:16]} WIB"


def _plus4h(iso) -> str:
    t = _dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    return (t + _dt.timedelta(hours=4)).isoformat()


def _pct(a, b) -> float:
    return (a / b - 1) * 100 if b else 0.0


# --------------------------------------------------------------------------- #
# template pesan
# --------------------------------------------------------------------------- #
def signal_message(p: dict, symbol: str, source: str, delay_min: float,
                   paper: dict) -> str:
    ctx = p.get("sig_ctx") or {}
    close0, stop, tgt = p["signal_close"], p["stop"], p["target"]
    risk_usd = paper["capital_usd"] * paper["risk_pct"] / 100.0
    qty = risk_usd / (close0 - stop) if close0 > stop else 0.0
    base = symbol.replace("USDT", "")
    late = (f"\n\n⚠️ <b>Terkirim {delay_min:.0f} menit setelah lilin tutup</b> — "
            "harga sudah bergerak dari open. Bot tetap mencatat entry di harga "
            "OPEN; kalau Anda ikut manual, catat harga fill Anda sendiri."
            if delay_min and delay_min > 15 else "")
    rsi0, rsi1 = ctx.get("rsi_bar0"), ctx.get("rsi_bar1")
    return f"""🟢 <b>SEQUENCE SNAP v2 — LONG</b>
{symbol} · 4H · lilin sinyal tutup {wib(_plus4h(p['signal_bar']))}

🎯 <b>Entry: market di OPEN lilin berikutnya</b>
close lilin sinyal: {f(close0)}

🛑 <b>Stop: {f(stop)}</b> ({_pct(stop, close0):+.2f}%, low lilin merah)
✅ <b>Target: {f(tgt)}</b> ({_pct(tgt, close0):+.2f}%, 1.5R)
Stop &amp; target dihitung dari CLOSE lilin sinyal. Tidak ada trailing, tidak ada batas waktu.

📐 <b>Ukuran posisi</b> (paper ${f(paper['capital_usd'], 0)}, risiko {f(paper['risk_pct'], 1)}% = ${f(risk_usd, 2)})
qty = {f(risk_usd, 2)} ÷ (harga entry − {f(stop)})
≈ {f(qty)} {base} · notional ≈ ${f(qty * close0, 2)}

📊 RSI {f(rsi0, 1)} (bar sebelumnya {f(rsi1, 1)}) · close {f(ctx.get('close_vs_ema200_pct'), 2)}% di atas EMA200 ({f(ctx.get('ema200_bar0'))})
<i>sumber: {esc(source)} · id: {p['signal_id']}</i>{late}"""


def entry_message(pos, symbol: str, source: str) -> str:
    dist = pos.entry_price - pos.stop
    return f"""📌 <b>ENTRY TERCATAT (paper) — {symbol}</b>
<code>open lilin {wib(pos.entry_bar)}</code>

  harga entry (open) : <b>{f(pos.entry_price)}</b>
  vs close sinyal    : {_pct(pos.entry_price, pos.signal_close):+.3f}%
  stop               : {f(pos.stop)}
  target             : {f(pos.target)}
  jarak risiko       : {f(dist)} ({dist / pos.entry_price * 100:.2f}%)
  qty paper          : {f(pos.qty)} · notional ${f(pos.qty * pos.entry_price, 2)}

<i>Kalau Anda ikut eksekusi manual, catat harga fill Anda di forward_test_log.csv.
sumber: {esc(source)} · id: {pos.signal_id}</i>"""


def exit_message(t: dict, symbol: str, summary: dict) -> str:
    win = t["R_net"] >= 0
    icon = "✅" if win else "🛑"
    arrow = "📈" if win else "📉"
    days = t["bars_held"] * 4 / 24
    rules = summary.get("stop_rules") or []
    warn = ("\n\n🚨 <b>ATURAN BERHENTI TERPICU</b>\n" + "\n".join(f"• {esc(r)}" for r in rules)
            if rules else "")
    return f"""{icon} <b>EXIT — {t['reason'].upper()} · {symbol}</b>
<code>kena di lilin {candle(t['exit_bar'])}</code>

{arrow} <b>{t['R_net']:+.2f} R bersih</b> ({t['R_gross']:+.2f} R kotor) · {usd(t['pnl_usd'])} paper
entry {f(t['entry_price'])} → exit {f(t['exit_price'])}
ditahan {t['bars_held']} lilin ({days:.1f} hari)
MAE {t['mae_pct']:+.2f}% · MFE {t['mfe_pct']:+.2f}%

📊 Total: {summary['n']} trade · {summary['sum_R']:+.2f} R · win rate {summary['win_rate']:.0f}%
kalah beruntun: {summary['losing_streak']} (batas 15) · drawdown paper {summary['drawdown_pct']:.1f}%
<i>id: {t['signal_id']}</i>{warn}"""


def _posline(sym, pos, last_close):
    tag = f"  {sym.replace('USDT', ''):<5}"
    if not pos:
        return f"{tag} —  menunggu sinyal"
    dist = pos["entry_price"] - pos["stop"]
    unreal = ((last_close - pos["entry_price"]) / dist) if (last_close and dist > 0) else None
    u = f" · {unreal:+.2f} R" if unreal is not None else ""
    return (f"{tag} LONG sejak {wib(pos['entry_bar'])}\n"
            f"        entry {f(pos['entry_price'])} · stop {f(pos['stop'])} · "
            f"target {f(pos['target'])}{u}")


def heartbeat_message(s: dict) -> str:
    lines = [_posline(sym, v.get("position"), v.get("last_close"))
             for sym, v in s["positions"].items()]
    n_open = sum(1 for v in s["positions"].values() if v.get("position"))
    down = s.get("symbols_down") or []
    down_line = ("\n⚠️ <b>data tidak terjangkau:</b> " + esc(", ".join(down))) if down else ""
    stuck = s.get("outbox_pending", 0)
    stuck_line = (f"\n⚠️ <b>{stuck} pesan belum terkirim</b> — dicoba ulang tiap run."
                  if stuck else "")
    sm = s["summary"]
    rules = sm.get("stop_rules") or []
    rules_line = ("\n\n🚨 <b>ATURAN BERHENTI TERPICU</b>\n"
                  + "\n".join(f"• {esc(r)}" for r in rules)) if rules else ""
    pnl = sm["pnl_usd"]
    return f"""💓 <b>Sequence Snap v2 — hidup</b>
<code>{wib(s['now'])}</code>

  lilin terakhir diproses: tutup {wib(_plus4h(s['last_bar'])) if s['last_bar'] else '-'}
  sumber data: {esc(s['source'])}
  posisi terbuka: {n_open} dari {len(s['positions'])}
{chr(10).join(lines)}{down_line}

  30 hari terakhir: {s['signals_30d']} sinyal · {s['trades_30d']} trade selesai
  total: {sm['n']} trade · {sm['sum_R']:+.2f} R · {usd(pnl)} (paper ${f(sm['equity_usd'], 2)})
  expectancy {sm['expectancy_R']:+.3f} R · win rate {sm['win_rate']:.0f}% · progres {sm['n']}/100
  drawdown paper {sm['drawdown_pct']:.1f}% (terdalam {sm['max_drawdown_pct']:.1f}%, batas −20%)
  kalah beruntun {sm['losing_streak']} (terpanjang {sm['longest_losing_streak']}, batas 15)

<i>Pesan ini muncul 1× sehari untuk memastikan bot masih jalan.
Sinyal dikirim terpisah, hanya kalau memang ada.</i>{stuck_line}{rules_line}"""


def alert_message(kind, detail) -> str:
    return (f"⚠️ <b>Sequence Snap — {esc(kind)}</b>\n\n<code>{esc(str(detail)[:600])}</code>\n\n"
            "<i>Sinyal mungkin tertunda sampai ini beres.</i>")
