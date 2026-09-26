"""Selesaikan konflik rebase di state/position.json berdasarkan ISI, bukan sisi.

Disalin dari Crypto-MEX. Saat push ditolak karena run lain menulis duluan, sisi
"mereka" biasanya yang lebih baru; memaksa sisi kita bisa memundurkan last_bar
dan memutar ulang bar yang sudah diproses.

  last_bar per simbol   yang lebih baru menang, dan position/pending diambil dari
                        sisi yang SAMA -- satu snapshot mesin state, tidak dicampur.
  sent_ids              gabungan. Pesan yang sudah terkirim di sisi mana pun tidak
                        boleh terkirim lagi.
  outbox                gabungan per kunci, dikurangi yang sudah ada di sent_ids.

Dipakai (di tengah rebase yang konflik): python tools/merge_state.py state/position.json
"""
import json
import subprocess
import sys


def _stage(n: int, path: str):
    """Tahap konflik: 2 = ours (upstream), 3 = theirs (yang sedang diputar ulang)."""
    try:
        raw = subprocess.run(["git", "show", f":{n}:{path}"],
                             capture_output=True, check=True).stdout
        return json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[merge_state] tahap {n} tidak terbaca: {type(e).__name__}")
        return None


def merge(a: dict | None, b: dict | None) -> dict | None:
    if a is None:
        return b
    if b is None:
        return a
    sa, sb = dict(a.get("symbols") or {}), dict(b.get("symbols") or {})

    def newest(st):
        return max([str(v.get("last_bar") or "") for v in (st.get("symbols") or {}).values()]
                   or [""])

    out = dict(a if newest(a) >= newest(b) else b)
    slots = {}
    for sym in set(sa) | set(sb):
        x, y = sa.get(sym), sb.get(sym)
        if x is None or y is None:
            slots[sym] = x if y is None else y
            continue
        slots[sym] = x if str(x.get("last_bar") or "") >= str(y.get("last_bar") or "") else y
    out["symbols"] = slots

    seen, sent = set(), []
    for sid in list(a.get("sent_ids") or []) + list(b.get("sent_ids") or []):
        if sid not in seen:
            seen.add(sid)
            sent.append(sid)
    out["sent_ids"] = sent

    outbox, keys = [], set()
    for m in list(a.get("outbox") or []) + list(b.get("outbox") or []):
        k = m.get("key")
        if k in keys or k in seen:
            continue
        keys.add(k)
        outbox.append(m)
    out["outbox"] = outbox

    hb = [d for d in (a.get("last_heartbeat_date"), b.get("last_heartbeat_date")) if d]
    if hb:
        out["last_heartbeat_date"] = max(hb)
    print(f"[merge_state] {len(slots)} simbol; sent_ids={len(sent)}; outbox={len(outbox)}")
    return out


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "state/position.json"
    ours, theirs = _stage(2, path), _stage(3, path)
    if ours is None and theirs is None:
        print("[merge_state] kedua sisi tidak terbaca, konflik tidak diselesaikan")
        return 1
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(merge(ours, theirs), fh, indent=2, default=str)
    subprocess.run(["git", "add", path], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
