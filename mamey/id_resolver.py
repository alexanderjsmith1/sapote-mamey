"""ID resolver — one row per BGC tying together the identifiers a reader needs to cross-reference.

    BGC_ID | bgc_uid | contig/NODE | region | antiSMASH file | workbook row

bgc_uid is composed in the master workbook, not stored in the bank. Pass a workbook_map for the
authoritative value; otherwise a derived best-effort uid is used (marked "(derived)") and workbook_row
is left blank — an honest blank, not a fabricated value (evidence conservation).
"""
from __future__ import annotations

COLUMNS = ["BGC_ID", "bgc_uid", "contig/NODE", "region", "antiSMASH_file", "workbook_row"]

def _derive_uid(b: dict) -> str:
    genus = (b.get("organism") or "").split()[0] if b.get("organism") else ""
    parts = [str(p) for p in (genus, b.get("sid"), b.get("bgc_id")) if p]
    return ("_".join(parts) + " (derived)") if parts else ""

def resolver_rows(bgcs: list, workbook_map: dict | None = None) -> list:
    wm = workbook_map or {}
    rows = []
    for b in bgcs:
        m = wm.get((b.get("sid"), b.get("bgc_id")), {})
        rows.append({
            "BGC_ID": b.get("bgc_id", ""),
            "bgc_uid": m.get("bgc_uid") or _derive_uid(b),
            "contig/NODE": b.get("contig", ""),
            "region": b.get("region", ""),
            "antiSMASH_file": b.get("source_kcb_file") or "",
            "workbook_row": m.get("row", ""),
        })
    return rows

def resolver_md(rows: list) -> str:
    if not rows:
        return "_(no BGCs to resolve)_"
    hdr = "| " + " | ".join(COLUMNS) + " |"
    sep = "|" + "|".join(["---"] * len(COLUMNS)) + "|"
    body = ["| " + " | ".join(str(r.get(c, "")) for c in COLUMNS) + " |" for r in rows]
    return "\n".join([hdr, sep] + body)
