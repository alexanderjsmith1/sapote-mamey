"""compound_family_report.py — anchored-BGC -> parent compound family -> AF/AB target class
-> known structure (roadmap #10).

FREEZE-SAFE ADDITIVE REPORT LAYER. Reads a *already-sealed* package's triage board
(``*_4_triage_board.csv``), maps each BGC's KCB/MIBiG anchor compound to its parent
compound family + a class-level target-class prior (AF / AB / siderophore / housekeeping /
…), attaches the KNOWN neighbour's structure via ``npatlas_structure``, and writes new
TSVs into a ``COMPOUND_FAMILIES/`` subfolder. It touches NO scan, scorer, tier, gate, or
lead-routing path — a re-run yields byte-identical triage. Non-blocking, like render-figures.

Distinct from ``compound_class.py`` (a *scoring* annotation layer: polyene_macrolide->AF).
This module is report-only: the target_class here is a literature ENCODED-CAPACITY prior for
the family the anchor belongs to, NEVER a claim the strain makes an active compound.
Comparators are similarity anchors, never identity; judgment deferred.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import glob
import collections
from pathlib import Path
from typing import Any

# whole-strain excludes (contaminated / chimeric) — never enter the AF/AB narrative.
# SSOT: raw-data module -> raw_analysis_excluded() = {AS-XXX, AS-XXX}. See OFFICIAL_DATA/EXCLUSIONS.md.
from .exclusions import raw_analysis_excluded
EXCLUDE_STRAINS = raw_analysis_excluded()

CLAIM_HEADER = (
    "# Compound-family report (freeze-safe additive layer). A KCB/MIBiG anchor is a SIMILARITY "
    "hit to the nearest characterised neighbour; target_class is the KNOWN literature bioactivity "
    "of that family used as a class-level ENCODED-CAPACITY prior, NOT a claim the strain makes an "
    "active compound. No structure/bioactivity claim beyond the evidence; judgment deferred."
)


# ---- rules -----------------------------------------------------------------------------------------
def _rules_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "compound_family_rules.json"


def load_rules(path: str | os.PathLike | None = None) -> list[tuple[list[str], tuple[str, str, str]]]:
    p = Path(path) if path else _rules_path()
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    return [(r["keys"], (r["family"], r["target_class"], r["moa"])) for r in data["rules"]]


def classify(anchor: str, rules=None) -> tuple[str, str, str]:
    """(parent_family, target_class, moa) for a compound anchor; ordered first-match-wins."""
    rules = rules if rules is not None else load_rules()
    a = (anchor or "").lower()
    for keys, val in rules:
        for k in keys:
            if k.lower() in a:
                return val
    return ("(unmapped specialised metabolite)", "other",
            "anchor present; parent family not in the curated map — needs manual lit lookup")


# ---- anchor extraction (reuse the engine's KCB parser when present) --------------------------------
def _extract_anchor(kcb_top: str) -> str | None:
    if not kcb_top or "|" not in kcb_top:
        return None
    try:  # prefer the vetted engine parser
        from mamey.npatlas_resolver import _extract_compound_name  # type: ignore
        return _extract_compound_name(kcb_top)
    except Exception:
        pass
    parts = [p.strip() for p in kcb_top.split("|")]
    if len(parts) < 2:
        return None
    name = parts[1].split("/")[0].strip()
    import re as _re
    name = _re.sub(r"\(.*?\)\s*$", "", name).strip()
    return name or None


def _find_triage_board(package_dir: str | os.PathLike) -> str | None:
    hits = sorted(glob.glob(os.path.join(str(package_dir), "*_4_triage_board.csv")))
    return hits[0] if hits else None


def _fnum(x):
    try:
        return float(x)
    except Exception:
        return None


def _strain_of(package_dir: str | os.PathLike, board: str) -> str:
    # prefer manifest; else the leading token of the board filename (AS-XXX_4_triage_board.csv)
    mp = os.path.join(str(package_dir), "manifest.json")
    if os.path.exists(mp):
        try:
            m = json.loads(Path(mp).read_text(encoding="utf-8"))
            for k in ("strain", "strain_id", "Strain"):
                if m.get(k):
                    return str(m[k])
        except Exception:
            pass
    return os.path.basename(board).split("_4_triage_board")[0]


# ---- main --------------------------------------------------------------------------------------------
def run(package_dir: str | os.PathLike, out_dir: str | os.PathLike | None = None,
        with_structures: bool = True) -> dict[str, Any]:
    """Classify a sealed package's anchored BGCs into compound families (+ structures). Returns a
    small summary dict; writes ANCHORED_BGC_COMPOUND_FAMILIES.tsv, COMPOUND_FAMILY_ROLLUP.tsv and
    (optionally) ANCHOR_STRUCTURES.tsv into <out_dir>/COMPOUND_FAMILIES/."""
    package_dir = str(package_dir)
    board = _find_triage_board(package_dir)
    if not board:
        return {"status": "no_triage_board", "note": "no *_4_triage_board.csv in package; skipped",
                "rows": 0}
    strain = _strain_of(package_dir, board)
    outd = os.path.join(str(out_dir or package_dir), "COMPOUND_FAMILIES")
    os.makedirs(outd, exist_ok=True)

    # v9.7.374 fix: was case-sensitive (same gap fixed for p450_tailoring.py at v9.7.371).
    # EXCLUDE_STRAINS (raw_analysis_excluded()) is canonical uppercase (e.g. "AS-XXX");
    # strain here comes from an arbitrary manifest.json string or a filename-derived
    # fallback, neither normalized. A differently-cased strain id silently bypassed this
    # whole-strain exclude gate and emitted a full compound-family report for a strain that
    # OFFICIAL_DATA/EXCLUSIONS.md policy says should produce none.
    if strain.strip().upper() in {s.upper() for s in EXCLUDE_STRAINS}:
        note = f"strain {strain} is on the whole-strain exclude list (contaminated/chimeric) — no family map emitted"
        with open(os.path.join(outd, "EXCLUDED.txt"), "w", encoding="utf-8") as fh:
            fh.write(note + "\n")
        return {"status": "excluded_strain", "strain": strain, "note": note, "rows": 0}

    rules = load_rules()
    rows: list[dict[str, Any]] = []
    with open(board, encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            anchor = _extract_anchor((d.get("KCB_top", "") or "").strip())
            if not anchor:
                continue
            fam, target, moa = classify(anchor, rules)
            rows.append(dict(
                strain=strain, bgc_id=d.get("BGC_ID", ""), anchor=anchor,
                parent_family=fam, target_class=target, moa=moa,
                products=d.get("Products", ""),
                AF=d.get("AF_auto", ""), AB=d.get("AB_auto", ""),
                novelty=d.get("Novelty_auto", ""), lead_tier=d.get("Lead_tier_auto", ""),
                kcb_score=d.get("KCB_score", ""),
            ))

    # per-BGC table
    cols = ["strain", "bgc_id", "anchor", "parent_family", "target_class", "moa",
            "products", "kcb_score", "AF", "AB", "novelty", "lead_tier"]
    with open(os.path.join(outd, "ANCHORED_BGC_COMPOUND_FAMILIES.tsv"), "w", newline="",
              encoding="utf-8") as fh:
        fh.write(CLAIM_HEADER + "\n")
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x["target_class"], x["parent_family"], x["bgc_id"])):
            w.writerow(r)

    # family rollup
    roll = collections.defaultdict(lambda: {"n": 0, "tc": "", "af": [], "ab": []})
    for r in rows:
        k = r["parent_family"]
        roll[k]["n"] += 1
        roll[k]["tc"] = r["target_class"]
        if _fnum(r["AF"]) is not None:
            roll[k]["af"].append(_fnum(r["AF"]))
        if _fnum(r["AB"]) is not None:
            roll[k]["ab"].append(_fnum(r["AB"]))

    def _med(xs):
        xs = sorted(xs)
        return "" if not xs else xs[len(xs) // 2]

    with open(os.path.join(outd, "COMPOUND_FAMILY_ROLLUP.tsv"), "w", newline="",
              encoding="utf-8") as fh:
        fh.write(CLAIM_HEADER + "\n")
        w = _SafeWriter(fh, delimiter="\t")
        w.writerow(["parent_family", "target_class", "n_bgcs", "median_AF_prior", "median_AB_prior"])
        for k, v in sorted(roll.items(), key=lambda kv: -kv[1]["n"]):
            w.writerow([k, v["tc"], v["n"], _med(v["af"]), _med(v["ab"])])

    result = {"status": "ok", "strain": strain, "rows": len(rows),
              "by_target_class": dict(collections.Counter(r["target_class"] for r in rows)),
              "unmapped": sum(1 for r in rows if r["parent_family"].startswith("(unmapped")),
              "out_dir": outd}

    # structures
    if with_structures:
        try:
            from mamey.npatlas_structure import resolve_name_to_structure  # type: ignore
        except Exception:
            try:
                from npatlas_structure import resolve_name_to_structure  # type: ignore
            except Exception:
                resolve_name_to_structure = None  # type: ignore
        if resolve_name_to_structure is not None:
            anchors: dict[str, dict[str, Any]] = {}
            for r in rows:
                a = r["anchor"]
                anchors.setdefault(a, {"family": r["parent_family"], "target": r["target_class"], "n": 0})
                anchors[a]["n"] += 1
            srows = []
            hit = 0
            for a, meta in sorted(anchors.items(), key=lambda kv: -kv[1]["n"]):
                s = resolve_name_to_structure(a)
                if s.get("inchikey"):
                    hit += 1
                srows.append({"anchor": a, "n_bgcs": meta["n"], "parent_family": meta["family"],
                              "target_class": meta["target"], "match": s["match_type"],
                              "matched_name": s["matched_name"], "npaid": s["npaid"],
                              "inchikey": s["inchikey"], "npclassifier_class": s["npclassifier_class"],
                              "smiles": s["smiles"]})
            scols = ["anchor", "n_bgcs", "parent_family", "target_class", "match", "matched_name",
                     "npaid", "inchikey", "npclassifier_class", "smiles"]
            with open(os.path.join(outd, "ANCHOR_STRUCTURES.tsv"), "w", newline="",
                      encoding="utf-8") as fh:
                fh.write("# Related-known-structure of each anchor's nearest characterised neighbour "
                         "(orientation only; NOT a product claim). Empty structure = no conservative "
                         "NP Atlas bind (never fabricated).\n")
                w = _SafeDictWriter(fh, fieldnames=scols, delimiter="\t", extrasaction="ignore")
                w.writeheader()
                for r in srows:
                    w.writerow(r)
            result["distinct_anchors"] = len(anchors)
            result["structures_resolved"] = hit
        else:
            result["structures"] = "npatlas_structure unavailable (add-on not installed)"

    return result


def compound_families_command(args) -> int:
    res = run(args.package, getattr(args, "out", None),
              with_structures=not getattr(args, "no_structures", False))
    emit(f"compound-families: {res.get('status')} | strain={res.get('strain','?')} | "
          f"anchored rows={res.get('rows', 0)}")
    if res.get("by_target_class"):
        emit("  by target class:", res["by_target_class"])
    if "structures_resolved" in res:
        emit(f"  structures: {res['structures_resolved']}/{res.get('distinct_anchors',0)} distinct "
              f"anchors resolved to an NP Atlas structure")
    if res.get("out_dir"):
        emit("  ->", res["out_dir"])
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Compound-family + structure report over a sealed package")
    ap.add_argument("package", help="path to a sealed package directory")
    ap.add_argument("--out", default=None, help="output root (default: the package dir)")
    ap.add_argument("--no-structures", action="store_true", help="skip NP Atlas structure resolution")
    a = ap.parse_args()
    raise SystemExit(compound_families_command(a))
