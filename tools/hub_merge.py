#!/usr/bin/env python3
"""hub_merge.py — one-shot hub merge: ingest → schema-gate → normalize → merge → verify.

Composes the G1 schema-drift discipline with the M1 normalize-then-append merge so the hub runs the whole
path in one deterministic step instead of ad hoc:

  1. INGEST       read the canonical workbook + every divergent source (column signatures).
  2. SCHEMA-GATE  compare each source's column signature to canonical (the workbook analog of G1's
                  manifest-signature check). Drift is FAIL-CLOSED unless a --mapping resolves it (or
                  --force-schema overrides). No drift + no mapping → a trivial direct mapping is synthesized.
  3. NORMALIZE    map each divergent source onto the canonical schema via the spec (M1).
  4. MERGE        append normalized rows under the canonical schema (M1).
  5. VERIFY       bgc_uid global uniqueness (fail-closed on collision), row-count reconcile, release/leak
                  tagging, blank-by-source ledger (M1).

  python tools/hub_merge.py --canonical A.xlsx --sources B.xlsx [C.xlsx ...] \
      [--mapping spec.xlsx] --out merged.xlsx [--report merged_report.md] [--force-schema]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text

import openpyxl

try:
    from tools import merge_workbooks as mw
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import merge_workbooks as mw


def _header(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet in wb.sheetnames else wb[wb.sheetnames[0]]
    hdr = [str(c) for c in next(ws.iter_rows(values_only=True))]
    wb.close()
    return hdr


def schema_gate(canon_cols, src_cols):
    """Workbook analog of the G1 manifest-signature check. Returns (verdict, detail)."""
    cs, ss = set(canon_cols), set(src_cols)
    canon_only = [c for c in canon_cols if c not in ss]
    source_only = [c for c in src_cols if c not in cs]
    drift = bool(canon_only or source_only)
    verdict = "NO_DRIFT" if not drift else "DRIFT"
    return verdict, {"canonical_only": canon_only, "source_only": source_only,
                     "shared": [c for c in canon_cols if c in ss]}


def _synth_direct_mapping(shared_cols):
    """For a no-drift source, build a trivial direct mapping spec so M1 can run unchanged."""
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Column_Mapping"
    ws.append(["canonical", "divergent", "action", "notes"])
    for c in shared_cols:
        ws.append([c, c, "direct", "auto (no drift)"])
    fd, path = tempfile.mkstemp(suffix=".xlsx"); os.close(fd)
    wb.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", required=True)
    ap.add_argument("--sources", nargs="+", required=True)
    ap.add_argument("--mapping", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--sheet", default=mw.SHEET_DEFAULT)
    ap.add_argument("--allow-collisions", action="store_true")
    ap.add_argument("--force-schema", action="store_true", help="proceed despite unresolved drift")
    a = ap.parse_args()

    # 1. INGEST
    canon_cols = _header(a.canonical, a.sheet)
    emit(f"① ingest: canonical {os.path.basename(a.canonical)} ({len(canon_cols)} cols), "
          f"{len(a.sources)} source(s)")

    # 2. SCHEMA-GATE (G1 discipline)
    gate_lines, any_drift = [], False
    for src in a.sources:
        sc = _header(src, a.sheet)
        verdict, d = schema_gate(canon_cols, sc)
        any_drift = any_drift or verdict == "DRIFT"
        gate_lines.append(f"{os.path.basename(src)}: {verdict} "
                          f"(+{len(d['source_only'])} renamed/extra, -{len(d['canonical_only'])} absent)")
    emit("② schema-gate: " + " | ".join(gate_lines))

    if any_drift and not a.mapping and not a.force_schema:
        emit("✗ SCHEMA DRIFT — sources diverge from the canonical column signature and no --mapping was "
              "given.\n  Refusing to merge (naive concatenation would silently misalign columns). Provide a "
              "--mapping spec to resolve, or --force-schema to override.")
        sys.exit(2)

    # 3+4. NORMALIZE + MERGE (M1). No drift + no mapping → synthesize a direct mapping.
    mapping = a.mapping
    synth = None
    if not mapping:
        shared = schema_gate(canon_cols, _header(a.sources[0], a.sheet))[1]["shared"]
        mapping = synth = _synth_direct_mapping(shared)
        emit("③ normalize: no mapping given + no drift → synthesized direct mapping")
    else:
        emit(f"③ normalize: mapping spec {os.path.basename(mapping)}")

    res = mw.run_merge(a.canonical, a.sources, mapping, a.out, a.report, a.sheet, a.allow_collisions)
    if synth:
        os.unlink(synth)

    # 5. VERIFY
    if res["status"] == "PK_COLLISION":
        emit(f"✗ VERIFY FAILED — {len(res['collisions'])} bgc_uid collision(s): "
              f"{', '.join(res['collisions'][:8])} (use --allow-collisions to override)")
        sys.exit(2)
    emit(f"④ merge: {res['rows']} rows -> {res['out']}", f"⑤ verify: bgc_uid unique ✓ | release {res['release']} | provenance-gap {len(res['prov_gap'])} | conserved {len(res['conserved'])}", sep="\n")

    if a.report:
        # v9.7.116: atomic append — read existing, append the gate section, atomic-rewrite the whole
        # file. A killed plain append can leave a half-written line in the existing report.
        _section = "\n## hub_merge schema-gate\n" + "\n".join(f"- {l}" for l in gate_lines) + "\n"
        _prior = ""
        if os.path.exists(a.report):
            with open(a.report) as _rf:
                _prior = _rf.read()
        atomic_write_text(a.report, _prior + _section)
    emit(f"✓ hub_merge complete{' (report -> ' + a.report + ')' if a.report else ''}")


if __name__ == "__main__":
    main()
