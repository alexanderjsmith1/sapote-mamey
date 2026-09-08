#!/usr/bin/env python3
"""merge_workbooks.py  (candidate patch M1)

Deterministic **normalize-then-append** merge for B1_BGC_Master workbooks. Given a canonical workbook, one
or more divergent workbooks, and a column-mapping spec, it normalizes every divergent source to the
canonical schema BEFORE appending — so the hub never naively concatenates divergent-schema tables (the
silent column-misalignment failure mode).

  python tools/merge_workbooks.py --canonical A.xlsx --sources B.xlsx [C.xlsx ...] \
      --mapping mapping_spec.xlsx --out merged.xlsx [--report merged_report.md] [--sheet B1_BGC_Master]

The mapping spec is the authoritative, reviewable contract (the 4-column sheet `Column_Mapping`:
`canonical | divergent | action | notes`). Actions: direct · RENAME · TRANSFORM · RENAME+TRANSFORM ·
BLANK · BLANK+FLAG (provenance gap) · MAP (→ conserved canonical col, target read from notes `→ name`) ·
DROP/move (e.g. inline taxonomy → A2_Strain_Registry).

Guarantees: honest blanks (never fabricated), evidence conservation (union of useful columns),
bgc_uid=strain:BGC_ID global-uniqueness check, per-source row-count reconcile, release/leak tagging
(any AS-### → PRIVATE), and a blank-by-source ledger. Fail-closed on PK collision unless --allow-collisions.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_save, atomic_write_text

# SSOT for the release tag (v9.7.236 PI decision: AS- is PUBLIC). Do not re-implement inline.
try:
    from mamey.dedup_and_guard import derive_release
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.dedup_and_guard import derive_release

import openpyxl
from openpyxl.styles import Font, PatternFill

SHEET_DEFAULT = "B1_BGC_Master"
PROVENANCE_FLAG = "KCB_PROVENANCE_COLUMNS_MISSING"

# Deterministic value transforms, addressed by NAME so the mapping spec selects them explicitly
# (`action=TRANSFORM=region_fmt`, or `transform=region_fmt` in notes). New divergent schemas reuse a
# named transform without touching code; an unknown name is left blank + raw conserved (never fabricated).
BOUNDARY = {"interior": "Interior", "edge": "Edge", "full-contig": "Full-contig", "full contig": "Full-contig"}


def _t_region(v):
    if isinstance(v, (int, float)) and v is not None:
        return f"region{int(v):03d}"
    return str(v) if v not in (None, "") else None


def _t_products(v):
    return v.replace("/", ";") if isinstance(v, str) else v


def _t_boundary(v):
    return BOUNDARY.get(str(v).strip().lower(), v) if v not in (None, "") else None


def _t_identity(v):
    return v


# name -> callable. Extend here; the spec references the name, not the column.
NAMED_TRANSFORMS = {
    "region_fmt": _t_region,                 # int 1 -> "region001"
    "delim_slash_to_semicolon": _t_products,  # "PKS/T1PKS" -> "PKS;T1PKS"
    "boundary_case": _t_boundary,             # "full-contig" -> "Full-contig"
    "identity": _t_identity,
}

# Backward-compat: legacy specs that say bare "TRANSFORM" with no name fall back to a transform inferred
# from the canonical column. New specs should name the transform explicitly.
DEFAULT_TRANSFORM_BY_CANON = {"region": "region_fmt", "products": "delim_slash_to_semicolon", "boundary": "boundary_case"}

_TX_NAME_RE = re.compile(r"transform\s*[=:]\s*([A-Za-z0-9_]+)", re.I)


def _resolve_transform_name(action, notes, canonical):
    """Pick the named transform: explicit in action (TRANSFORM=name / TRANSFORM:name) or notes
    (transform=name), else the canonical-column default (legacy), else None (-> blank + conserve raw)."""
    m = re.search(r"TRANSFORM\s*[=:]\s*([A-Za-z0-9_]+)", action or "", re.I)
    if m:
        return m.group(1).lower()
    m = _TX_NAME_RE.search(notes or "")
    if m:
        return m.group(1).lower()
    return DEFAULT_TRANSFORM_BY_CANON.get(canonical)


def _read_sheet(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if sheet in wb.sheetnames:
        ws = wb[sheet]
    else:
        import warnings
        ws = wb[wb.sheetnames[0]]
        warnings.warn(f"Sheet '{sheet}' not found in {path}; falling back to '{wb.sheetnames[0]}'")
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(c) for c in rows[0]]
    data = [dict(zip(hdr, r)) for r in rows[1:] if r and r[0] is not None]
    extra = {sn: wb[sn] for sn in wb.sheetnames}  # for taxonomy lookup etc.
    wb.close()
    return hdr, data


def parse_mapping(path):
    """Return per-divergent-column rules: {b_col: {'canonical':.., 'action':.., 'notes':..}} plus the
    provenance-gap set and any MAP→conserved-target names and taxonomy handling."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Column_Mapping"] if "Column_Mapping" in wb.sheetnames else wb[wb.sheetnames[0]]
    rules = {}
    prov_gap = []
    conserved = {}      # b_col -> canonical conserved name
    taxonomy_to_a2 = None
    rows = list(ws.iter_rows(values_only=True))
    for r in rows[1:]:
        if not r or all(c is None for c in r):
            continue
        canon = str(r[0]).strip() if r[0] else ""
        bcol = str(r[1]).strip() if r[1] else ""
        action = (str(r[2]).strip() if r[2] else "").upper()
        notes = str(r[3]).strip() if len(r) > 3 and r[3] else ""
        if not bcol or bcol.lower() in ("(missing)",):
            if "BLANK+FLAG" in action or "PROVENANCE GAP" in notes.upper():
                prov_gap.append(canon)
            continue
        if "DROP" in action or "A2" in action.upper() or "A2" in notes.upper():
            if bcol.lower() == "taxonomy":
                taxonomy_to_a2 = bcol
            continue
        if "MAP" in action and canon.startswith("("):
            m = re.search(r"->|→", notes)
            target = re.split(r"->|→", notes)[-1].strip().split()[0] if m else bcol.lower()
            conserved[bcol] = target
            continue
        rules[bcol] = {"canonical": canon, "action": action, "notes": notes,
                       "transform": _resolve_transform_name(action, notes, canon) if "TRANSFORM" in action else None}
        if "BLANK+FLAG" in action:
            prov_gap.append(canon)
    wb.close()
    return rules, prov_gap, conserved, taxonomy_to_a2


def normalize_row(brow, rules, conserved, canon_cols):
    out = {c: None for c in canon_cols}
    for bcol, rule in rules.items():
        canon = rule["canonical"]
        if canon not in out:
            continue
        v = brow.get(bcol)
        act = rule["action"]
        if "TRANSFORM" in act:
            fn = NAMED_TRANSFORMS.get(rule.get("transform"))
            out[canon] = fn(v) if fn else None  # unknown/unnamed transform -> blank (raw conserved below)
        else:  # direct / RENAME
            out[canon] = v
    cons = {}
    for bcol, target in conserved.items():
        cons[target] = brow.get(bcol)
    # conserve raw value of any TRANSFORM whose named transform is unknown (no fabrication, no data loss)
    for bcol, rule in rules.items():
        if "TRANSFORM" in rule["action"] and rule["canonical"] in canon_cols and NAMED_TRANSFORMS.get(rule.get("transform")) is None:
            cons[bcol.lower()] = brow.get(bcol)
    return out, cons


def run_merge(canonical, sources, mapping, out, report=None, sheet=SHEET_DEFAULT, allow_collisions=False):
    """Importable merge core. Returns a result dict; on PK collision (and not allow_collisions) returns
    status='PK_COLLISION' WITHOUT writing, so callers (e.g. the hub command) can fail-closed themselves."""
    import types
    a = types.SimpleNamespace(canonical=canonical, sources=sources, mapping=mapping, out=out,
                              report=report, sheet=sheet, allow_collisions=allow_collisions)

    canon_cols, A = _read_sheet(a.canonical, a.sheet)
    rules, prov_gap, conserved, tax_col = parse_mapping(a.mapping)
    conserved_targets = sorted(set(conserved.values()))

    rows = []
    src_counts = {os.path.basename(a.canonical): len(A)}
    a2 = []  # (strain, taxonomy, source, release)
    seen_strain = set()
    # canonical rows first (untouched; blank for conserved + any extra raw)
    for r in A:
        row = {c: r.get(c) for c in canon_cols}
        for t in conserved_targets:
            row.setdefault(t, None)
        row["_src"] = os.path.basename(a.canonical)
        rows.append(row)
        for s in [r.get("strain")]:
            if s and s not in seen_strain:
                a2.append((s, None, os.path.basename(a.canonical), None)); seen_strain.add(s)

    extra_conserved = set(conserved_targets)
    for src in a.sources:
        hdrB, B = _read_sheet(src, a.sheet)
        src_counts[os.path.basename(src)] = len(B)
        for br in B:
            norm, cons = normalize_row(br, rules, conserved, canon_cols)
            # frozen-schema default: product present but no manual-check value -> 'yes'
            if norm.get("products") and not norm.get("needs_manual_kcb_check"):
                norm["needs_manual_kcb_check"] = "yes"
            for k, v in cons.items():
                norm[k] = v; extra_conserved.add(k)
            norm["_src"] = os.path.basename(src)
            rows.append(norm)
            s = br.get("strain")
            tax = br.get(tax_col) if tax_col else None
            if s and s not in seen_strain:
                a2.append((s, tax, os.path.basename(src), None)); seen_strain.add(s)

    # ---- verification ----
    for r in rows:
        r["bgc_uid"] = f"{r.get('strain')}:{r.get('BGC_ID')}"
    uids = [r["bgc_uid"] for r in rows]
    from collections import Counter
    _uid_counts = Counter(uids)
    dups = sorted(u for u, c in _uid_counts.items() if c > 1)
    private = any(derive_release(r.get("strain")) == "PRIVATE" for r in rows)
    release = "PRIVATE" if private else "PUBLIC"
    a2 = [(s, t, src, release) for (s, t, src, _) in a2]

    out_cols = ["bgc_uid"] + canon_cols + sorted(extra_conserved)

    if dups and not a.allow_collisions:
        return {"status": "PK_COLLISION", "collisions": dups, "rows": len(rows),
                "release": release, "out": None}

    # ---- write ----
    wb = openpyxl.Workbook()
    arial = Font(name="Arial", size=10)
    hf = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="1A2F4A")

    ws = wb.active; ws.title = a.sheet
    ws.append(out_cols)
    for j in range(1, len(out_cols) + 1):
        ws.cell(1, j).font = hf; ws.cell(1, j).fill = fill
    for r in rows:
        ws.append([r.get(c) for c in out_cols])
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = arial

    reg = wb.create_sheet("A2_Strain_Registry")
    reg.append(["strain", "taxonomy", "source_workbook", "release"])
    for j in range(1, 5):
        reg.cell(1, j).font = hf; reg.cell(1, j).fill = fill
    for tup in a2:
        reg.append(list(tup))
    for row in reg.iter_rows(min_row=2):
        for c in row:
            c.font = arial

    lg = wb.create_sheet("_MERGE_LEDGER")
    lg.append(["canonical_column", "rows_filled", "note"])
    for j in range(1, 4):
        lg.cell(1, j).font = hf; lg.cell(1, j).fill = fill
    for c in canon_cols + sorted(extra_conserved):
        filled = sum(1 for r in rows if r.get(c) not in (None, ""))
        note = ""
        if c in prov_gap:
            note = f"PROVENANCE GAP ({PROVENANCE_FLAG})"
        elif c in extra_conserved:
            note = "evidence conserved from divergent source"
        lg.append([c, filled, note])
    for row in lg.iter_rows(min_row=2):
        for c in row:
            c.font = arial

    info = wb.create_sheet("_SCHEMA_INFO")
    summary = [
        "MERGED via merge_workbooks.py (normalize-then-append)",
        f"canonical: {os.path.basename(a.canonical)} ({len(canon_cols)} cols)",
        f"sources: {', '.join(os.path.basename(s) for s in a.sources)}",
        f"rows: {' + '.join(f'{k}={v}' for k, v in src_counts.items())} = {len(rows)}",
        f"bgc_uid unique: {len(set(uids))}/{len(uids)} | collisions: {len(dups)}",
        f"release: {release}",
        f"provenance-gap flagged: {', '.join(prov_gap) or 'none'}",
        f"conserved columns: {', '.join(sorted(extra_conserved)) or 'none'}",
    ]
    for line in summary:
        info.append([line]); info.cell(info.max_row, 1).font = arial
    atomic_save(wb, a.out)  # v9.7.116: atomic save — a killed write must not corrupt the merged deliverable into a BadZipFile

    summary_str = "\n".join(f"- {s}" for s in summary)
    if a.report:
        atomic_write_text(a.report, "# Merge report (merge_workbooks.py)\n\n" + summary_str + "\n")

    return {"status": "OK", "rows": len(rows), "collisions": dups, "release": release,
            "out": a.out, "report": a.report, "summary": summary, "src_counts": src_counts,
            "prov_gap": prov_gap, "conserved": sorted(extra_conserved), "out_cols": out_cols}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical")
    ap.add_argument("--sources", nargs="+")
    ap.add_argument("--mapping")
    ap.add_argument("--out")
    ap.add_argument("--report", default=None)
    ap.add_argument("--sheet", default=SHEET_DEFAULT)
    ap.add_argument("--allow-collisions", action="store_true")
    ap.add_argument("--list-transforms", action="store_true", help="print the named-transform registry and exit")
    a = ap.parse_args()

    if a.list_transforms:
        emit("named transforms (referenced by the mapping spec via TRANSFORM=<name> or transform=<name>):")
        for n in NAMED_TRANSFORMS:
            emit(f"  {n}")
        emit("legacy fallback by canonical column:", DEFAULT_TRANSFORM_BY_CANON)
        return
    if not (a.canonical and a.sources and a.mapping and a.out):
        ap.error("--canonical, --sources, --mapping and --out are required (unless --list-transforms)")

    res = run_merge(a.canonical, a.sources, a.mapping, a.out, a.report, a.sheet, a.allow_collisions)
    if res["status"] == "PK_COLLISION":
        emit(f"✗ PK COLLISION — {len(res['collisions'])} duplicate bgc_uid(s): {', '.join(res['collisions'][:8])}", "  Refusing to write a merge with colliding primary keys (use --allow-collisions to override).", sep="\n")
        sys.exit(2)
    emit(f"✓ merged {res['rows']} rows -> {res['out']}", f"  bgc_uid unique, {len(res['collisions'])} collisions | release {res['release']}", f"  provenance-gap: {len(res['prov_gap'])} cols | conserved: {len(res['conserved'])} cols", sep="\n")
    if res["report"]:
        emit(f"  report -> {res['report']}")


if __name__ == "__main__":
    main()
