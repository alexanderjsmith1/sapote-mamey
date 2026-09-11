#!/usr/bin/env python3
"""build_wetlab_matrix.py — deterministic writer for the Wet-Lab Decision Matrix (WLDM).

Promotes docs/modules/DELIVERABLE_WetLabMatrix.md from PROMPT_BACKED to SCHEMA_BACKED: the score now lives in
score_bgc() here (single source of truth), and the module becomes its portable spec. Implements the §3a base
score + LMPKS adjustment + decision categories + the four independent action scores (§3b), reading only fields
the Mamey package actually carries and citing each term's source field. Skip-not-fake: any term whose input is
absent is omitted and labelled, never assumed (RiQ and per-BGC TFBS-induction are absent in current packages).

Inputs (Mamey package):
  manifest.json -> bgc_counts.assembly_tier, bioactivity, bgcs[].{edge_status, architecture_confidence,
                   kcb_cumulative, kcb_top, riq_score, products, contig_length, length_kb}
  manifest.json -> source_scans.blda_tta.per_bgc[bgc].bldA_tier        (T3/T4 gating term)

Outputs:
  <strain>_WetLab_Decision_Matrix.csv   (primary deterministic artifact)
  <strain>_WetLab_Decision_Matrix.xlsx  (sheet 'WetLab_Decision_Matrix' for workbook merge)

Usage:
  python tools/build_wetlab_matrix.py --package-dir <pkg> --out-dir <dir>
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, json, os, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_save


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


def _prodstr(p):
    return (" ".join(p) if isinstance(p, list) else (p or "")).lower()

# ---- the score (single source of truth; §3a portable table is its spec) -------------------------
def score_bgc(b, blda_tier, bioactivity_on=False):
    """Return (base_score, [(term, points, source_field)...], notes[])."""
    terms = []; notes = []
    arch = (b.get("architecture_confidence") or "").upper()
    edge = b.get("edge_status") or ""
    kcb = float(b.get("kcb_cumulative") or b.get("kcb_top") or 0)
    riq = b.get("riq_score")
    prod = _prodstr(b.get("products"))

    if edge == "Interior":
        terms.append(("Interior BGC", 3, "edge_status"))
    if arch == "A":
        terms.append(("Architecture A", 3, "architecture_confidence"))
    elif arch == "B":
        terms.append(("Architecture B", 2, "architecture_confidence"))
    elif arch == "C":
        terms.append(("Architecture C (pathway unit)", 1, "architecture_confidence"))

    if kcb > 5000:
        terms.append(("Strong KCB >5,000", 3, "kcb_cumulative"))
    elif kcb == 0:
        if arch == "A":
            terms.append(("No KCB + strong diagnostic (Arch A)", 4, "kcb_cumulative+architecture_confidence"))
        elif arch == "B":
            terms.append(("No KCB + moderate (Arch B)", 2, "kcb_cumulative+architecture_confidence"))

    if riq in (None, "", "-"):
        notes.append("RiQ: not computed")
    else:
        r = float(riq)
        if r < 0.50:
            terms.append(("RiQ <0.50 coherent", 3, "riq_score"))
        elif r <= 0.85:
            terms.append(("RiQ 0.50-0.85 unusual tailoring", 2, "riq_score"))

    notes.append("induction: not per-BGC (tfbs genome-wide only)")  # skip-not-fake

    if blda_tier in ("T3", "T4"):
        terms.append((f"bldA {blda_tier} gating", 2, "source_scans.blda_tta.bldA_tier"))

    # Metadata does not alter deterministic prioritization under this contract.
    # A future evidence-and-scoring authority would need to add any nonzero term.

    if edge in ("Edge", "Full-Contig", "FC"):
        terms.append(("edge/FC truncation", -2, "edge_status"))

    # tiny unanchored fragment: small region on an edge with no KCB anchor
    length_kb = b.get("length_kb")
    if length_kb is None and b.get("start") is not None and b.get("end") is not None:
        length_kb = (b["end"] - b["start"]) / 1000.0
    if length_kb is not None and length_kb < 5 and edge != "Interior" and kcb == 0:
        terms.append(("tiny unanchored fragment", -3, "length_kb+edge_status"))

    notes.append("LMPKS: not run")  # post-score adjustment requires a rescue result; skip-not-fake

    base = sum(p for _, p, _ in terms)
    return base, terms, notes


def decision_category(score):
    if score >= 10: return "Immediate follow-up"
    if score >= 7:  return "Strong follow-up"
    if score >= 4:  return "Conditional follow-up"
    if score >= 1:  return "Inventory only"
    return "Deprioritized"


def action_scores(b, base, blda_tier):
    arch = (b.get("architecture_confidence") or "").upper()
    edge = b.get("edge_status") or ""
    kcb = float(b.get("kcb_cumulative") or b.get("kcb_top") or 0)
    riq = b.get("riq_score")
    seq = "HIGH" if (edge in ("Edge", "Full-Contig", "FC") or arch == "C") else "LOW"
    act = "HIGH" if blda_tier in ("T3", "T4") else "LOW"   # TFBS-induction half is not per-BGC; bldA carries it
    iso = "HIGH" if base >= 10 else ("MED" if base >= 7 else "LOW")
    if kcb > 1000:
        der = "HIGH"
    elif riq not in (None, "", "-") and float(riq) > 0.50:
        der = "HIGH"
    else:
        der = "LOW"
    return seq, act, iso, der


def locator(b):
    contig = b.get("contig") or b.get("node_id") or "?"
    reg = b.get("region_number") or b.get("antismash_region") or "?"
    return f"{b['bgc_id']} ({contig} · region{reg})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    mf = glob.glob(os.path.join(a.package_dir, "manifest.json"))
    if not mf:
        raise SystemExit("manifest.json not found in package dir")
    d = _read_json(mf[0])
    strain = d.get("strain_id") or "STRAIN"
    blda = ((d.get("source_scans", {}) or {}).get("blda_tta", {}) or {}).get("per_bgc", {}) or {}
    bioact_on = False
    os.makedirs(a.out_dir, exist_ok=True)

    rows = []
    for b in d.get("bgcs", []):
        bt = (blda.get(b["bgc_id"]) or {}).get("bldA_tier")
        base, terms, notes = score_bgc(b, bt, bioact_on)
        cat = decision_category(base)
        seq, act, iso, der = action_scores(b, base, bt)
        rows.append({
            "locator": locator(b), "bgc_id": b["bgc_id"], "products": _prodstr(b.get("products")),
            "score": base, "decision_category": cat,
            "seq_priority": seq, "activation_priority": act, "isolation_priority": iso, "dereplication_priority": der,
            "score_breakdown": "; ".join(f"{t}{'+' if p >= 0 else ''}{p} [{src}]" for t, p, src in terms),
            "skip_notes": "; ".join(notes),
        })
    rows.sort(key=lambda r: -r["score"])

    csv_path = os.path.join(a.out_dir, f"{strain}_WetLab_Decision_Matrix.csv")
    # Empty-safe write (v9.7.114): a strain with zero scored BGCs must write a valid header-only CSV.
    _FIELDS = ["locator", "bgc_id", "products", "score", "decision_category",
               "seq_priority", "activation_priority", "isolation_priority", "dereplication_priority",
               "score_breakdown", "skip_notes"]
    fieldnames = list(rows[0].keys()) if rows else _FIELDS
    _tmp = csv_path + ".tmp"
    with open(_tmp, "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
    os.replace(_tmp, csv_path)

    try:
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "WetLab_Decision_Matrix"
        ws.append(fieldnames)
        for r in rows: ws.append([(", ".join(v) if isinstance(v,list) else v) for v in (r[k] for k in fieldnames)])
        xlsx_path = os.path.join(a.out_dir, f"{strain}_WetLab_Decision_Matrix.xlsx")
        # v9.7.371 fix: was a bare wb.save(xlsx_path) -- the CSV sibling written 4 lines above
        # correctly hand-rolls the tmp+os.replace() pattern; this XLSX write did not, so a process
        # killed mid-save left a truncated/corrupt .xlsx (tools/_wbio.py's own docstring: "corrupts
        # the workbook into an unreadable BadZipFile") sitting next to its intact CSV sibling in
        # the deliverables directory. atomic_save is the same tmp+os.replace helper already used
        # elsewhere in this codebase for exactly this write pattern.
        atomic_save(wb, xlsx_path)
    except Exception as e:
        xlsx_path = f"(xlsx skipped: {e})"

    cats = {}
    for r in rows: cats[r["decision_category"]] = cats.get(r["decision_category"], 0) + 1
    emit(f"{strain}: {len(rows)} BGCs scored -> {csv_path}", f"  categories: {cats}", f"  xlsx: {xlsx_path}", sep="\n")


if __name__ == "__main__":
    main()
