"""Mirror Google Sheets lewat service account. Disalin dari Crypto-MEX (mex/sheets.py).

  GOOGLE_SERVICE_ACCOUNT_JSON + GSHEET_SPREADSHEET_ID
      Masuk sebagai service account dan memanggil Sheets API langsung. Akses
      bisa dicabut dengan berhenti membagikan spreadsheet ke service account.

CSV di state/ tetap catatan resmi; Sheets hanya cermin. Gagal menulis ke
Sheets tidak pernah menggagalkan run.

Nothing here ever prints a secret's value. A service-account key pasted into the
wrong place once leaked a private key into this repo's public workflow logs via
a library exception message, so exceptions are reported by type only and the
client_email -- an identifier, not a credential -- is the single field ever
echoed, because the user needs it to share the spreadsheet.
"""
from . import compat  # noqa: F401
import json
import os

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
API = "https://sheets.googleapis.com/v4/spreadsheets"

_session = None
_tab_header: dict[str, list[str]] = {}


def configured() -> bool:
    return bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
                and os.environ.get("GSHEET_SPREADSHEET_ID", "").strip())


def _spreadsheet_id() -> str:
    return os.environ.get("GSHEET_SPREADSHEET_ID", "").strip()


def client_email() -> str:
    """The address the spreadsheet must be shared with. Not a credential."""
    try:
        return json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]).get("client_email", "")
    except Exception:  # noqa: BLE001
        return ""


def missing() -> str | None:
    """What is still needed before the mirror can work, phrased as an action.

    Half-configured is the easy state to land in -- the key alone tells us
    nothing about which spreadsheet to write to -- and it would otherwise look
    identical to "not configured at all" in the logs.
    """
    has_key = bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip())
    has_id = bool(_spreadsheet_id())
    if has_key and not has_id:
        return ("GSHEET_SPREADSHEET_ID belum diisi. Ambil ID dari URL spreadsheet "
                "(bagian antara /d/ dan /edit), simpan sebagai secret repo, lalu "
                f"bagikan spreadsheet itu ke {client_email()} dengan akses Editor.")
    if has_id and not has_key:
        return "GOOGLE_SERVICE_ACCOUNT_JSON belum diisi."
    return None


def _get_session():
    global _session
    if _session is not None:
        return _session
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    _session = AuthorizedSession(creds)
    return _session


def _header(s, tab: str, want: list[str]) -> list[str]:
    """The tab's OWN header row, extended with any column it does not have yet.

    ledger._rotate() protects the CSV logs from a column-list change: DictWriter
    writes positionally, so a new row under an old header lands in the wrong
    columns, and the fix is to archive the old file and start a clean one. This
    function is the half of that guard the mirror never had. append() used to
    send values ordered by EVENT_COLS into whatever header the tab already
    carried, so a tab created by the Apps Script path -- whose header comes from
    a row's dict key order, not from EVENT_COLS -- received 17 of 19 columns
    under the wrong name and spilled 26 more past the end of the header, while
    still reporting success to sheet_status().

    Rows are matched BY NAME instead. A column the sheet has never seen is
    appended on the right; nothing already in the sheet is moved or rewritten,
    so historical rows stay aligned with the names above them.
    """
    if tab in _tab_header:
        return _tab_header[tab]
    sid = _spreadsheet_id()
    meta = s.get(f"{API}/{sid}?fields=sheets.properties.title", timeout=30)
    meta.raise_for_status()
    titles = [sh["properties"]["title"] for sh in meta.json().get("sheets", [])]
    if tab not in titles:
        s.post(f"{API}/{sid}:batchUpdate", timeout=30,
               json={"requests": [{"addSheet": {"properties": {"title": tab}}}]}
               ).raise_for_status()
    first = s.get(f"{API}/{sid}/values/{tab}!1:1", timeout=30)
    first.raise_for_status()
    rows = first.json().get("values") or [[]]
    # Only TRAILING blanks are dropped. A blank cell in the MIDDLE of the header
    # is a column position, and squeezing it out would shift every name to its
    # right one column left -- relabelling every historical row underneath them,
    # which is the exact corruption this function exists to prevent.
    have = [str(c) for c in rows[0]]
    while have and not have[-1].strip():
        have.pop()
    head = list(want) if not have else have + [c for c in want if c not in have]
    if head != have:
        # Writing across A1 touches the header row only, and every name already
        # present keeps its column, so no existing row is disturbed.
        s.put(f"{API}/{sid}/values/{tab}!A1?valueInputOption=RAW", timeout=30,
              json={"values": [head]}).raise_for_status()
        if have:
            print(f"[sheets] header '{tab}' diperluas "
                  f"{len(have)} -> {len(head)} kolom (kolom lama tidak digeser)")
    _tab_header[tab] = head
    return head


def append(tab: str, header: list[str], row: dict) -> bool:
    """Append one row, columns matched to the tab's own header by name. Never raises."""
    if not configured():
        return False
    try:
        s = _get_session()
        cols = _header(s, tab, header)
        values = [["" if row.get(k) is None else row.get(k, "") for k in cols]]
        r = s.post(
            f"{API}/{_spreadsheet_id()}/values/{tab}!A1:append"
            "?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
            json={"values": values}, timeout=30)
        if r.status_code >= 400:
            # Status only. Response bodies from Google echo the request URL, and
            # GitHub's masking does not cover a multi-line secret.
            print(f"[sheets] HTTP {r.status_code} saat menulis ke '{tab}'")
            if r.status_code in (403, 404):
                print(f"[sheets] bagikan spreadsheet ke: {client_email()} (akses Editor)")
            return False
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[sheets] gagal: {type(e).__name__}")
        return False


def reachable() -> bool:
    """Can we read the spreadsheet's metadata? Adds no rows."""
    if not configured():
        return False
    try:
        s = _get_session()
        r = s.get(f"{API}/{_spreadsheet_id()}?fields=spreadsheetId", timeout=30)
        if r.status_code >= 400:
            print(f"[sheets] probe HTTP {r.status_code}; "
                  f"bagikan spreadsheet ke: {client_email()} (akses Editor)")
            return False
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[sheets] probe gagal: {type(e).__name__}")
        return False


# --------------------------------------------------------------------------- #
# Tambahan Sequence Snap: baca balik, sinkron dari CSV, dan tab ringkasan.
# --------------------------------------------------------------------------- #
def read(tab: str) -> list[list[str]] | None:
    """Seluruh isi tab (termasuk header), atau None kalau gagal. Tab yang belum
    ada dikembalikan sebagai [] -- bukan error."""
    if not configured():
        return None
    try:
        s = _get_session()
        r = s.get(f"{API}/{_spreadsheet_id()}/values/{tab}", timeout=30)
        if r.status_code == 400:
            return []                       # tab belum ada
        if r.status_code >= 400:
            print(f"[sheets] HTTP {r.status_code} saat membaca '{tab}'")
            return None
        return r.json().get("values") or []
    except Exception as e:  # noqa: BLE001
        print(f"[sheets] baca '{tab}' gagal: {type(e).__name__}")
        return None


def sync(tab: str, header: list[str], rows: list[dict]) -> int | None:
    """Tambahkan baris CSV yang belum ada di tab. Mengembalikan jumlah baris yang
    ditambahkan, atau None kalau gagal. Tidak pernah raise.

    CSV adalah catatan resmi dan hanya bertambah di belakang, jadi "belum ada"
    = baris CSV ke-(n+1) dan seterusnya, dengan n = jumlah baris data di tab.
    Ini yang memulihkan baris yang dulu gagal dicerminkan (Sheets sempat mati).
    """
    if not configured():
        return None
    try:
        s = _get_session()
        cols = _header(s, tab, header)
        have = read(tab)
        if have is None:
            return None
        n = max(0, len(have) - 1)
        todo = rows[n:]
        if not todo:
            return 0
        values = [["" if r.get(k) is None else r.get(k, "") for k in cols] for r in todo]
        r = s.post(f"{API}/{_spreadsheet_id()}/values/{tab}!A1:append"
                   "?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
                   json={"values": values}, timeout=60)
        if r.status_code >= 400:
            print(f"[sheets] HTTP {r.status_code} saat sinkron '{tab}'")
            return None
        return len(todo)
    except Exception as e:  # noqa: BLE001
        print(f"[sheets] sinkron '{tab}' gagal: {type(e).__name__}")
        return None


def replace(tab: str, values: list[list]) -> bool:
    """Timpa seluruh isi tab (dipakai untuk tab ringkasan). Tidak pernah raise."""
    if not configured():
        return False
    try:
        s = _get_session()
        sid = _spreadsheet_id()
        meta = s.get(f"{API}/{sid}?fields=sheets.properties.title", timeout=30)
        meta.raise_for_status()
        titles = [sh["properties"]["title"] for sh in meta.json().get("sheets", [])]
        if tab not in titles:
            s.post(f"{API}/{sid}:batchUpdate", timeout=30,
                   json={"requests": [{"addSheet": {"properties": {"title": tab}}}]}
                   ).raise_for_status()
        s.post(f"{API}/{sid}/values/{tab}:clear", json={}, timeout=30).raise_for_status()
        r = s.put(f"{API}/{sid}/values/{tab}!A1?valueInputOption=RAW", timeout=30,
                  json={"values": [["" if v is None else v for v in row] for row in values]})
        if r.status_code >= 400:
            print(f"[sheets] HTTP {r.status_code} saat menulis '{tab}'")
            return False
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[sheets] tulis '{tab}' gagal: {type(e).__name__}")
        return False
