"""assembly_line.py — deterministic PKS/NRPS assembly-line reader (roadmap #6, report layer).

FREEZE-SAFE ADDITIVE REPORT LAYER. Turns a BGC's class TOKEN ("T1PKS", "NRPS") into the actual
predicted assembly LOGIC by walking the ordered antiSMASH aSDomain rows of the native seal-path
file ``{strain}_domains.csv`` (written by gene_context.write_gene_context; columns bgc_id,
locus_tag, feature_type, domain, substrate, start, …): the NRPS monomer sequence (A-domain
substrates), the PKS extender sequence (AT substrates), module count, release (TE) and D-config
(Epimerization) signals, plus a class-consistency read.

Reads a native package file, writes new files only → touches NO scan/scorer/tier/gate; re-run
yields identical triage. Non-blocking, like render-figures.

This is the REPORT half of module-role extraction (see MODULE_ROLE_EXTRACTION_SCOPE.md). The SCORING
half (feeding module-role complementarity into rggmci for the two-proof) is a separate re-score item.

CLAIM CEILING (mandatory): substrate/module calls are antiSMASH Stachelhaus/Minowa PREDICTIONS
(similarity-level, lower bounds if edge-truncated); NOT a structure/product/stereochemistry claim.
Judgment deferred.
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
import glob
import os
import json
import collections
from pathlib import Path
from typing import Any

# SSOT: raw-data module -> raw_analysis_excluded() = {AS-XXX, AS-XXX}. See OFFICIAL_DATA/EXCLUSIONS.md.
from .exclusions import raw_analysis_excluded
EXCLUDE_STRAINS = raw_analysis_excluded()
CLAIM_HEADER = (
    "# Assembly-line report (freeze-safe additive layer). Substrate/module calls are antiSMASH "
    "Stachelhaus/Minowa PREDICTIONS (similarity-level, lower bounds if edge-truncated); NOT a "
    "structure/product/stereochemistry claim. Judgment deferred."
)


def _find_domains_csv(package_dir: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(package_dir, "*_domains.csv")))
    return hits[0] if hits else None


def _strain_of(package_dir: str, domains_csv: str) -> str:
    mp = os.path.join(package_dir, "manifest.json")
    if os.path.exists(mp):
        try:
            m = json.loads(Path(mp).read_text(encoding="utf-8"))
            for k in ("strain", "strain_id", "Strain"):
                if m.get(k):
                    return str(m[k])
        except Exception:
            pass
    return os.path.basename(domains_csv).split("_domains.csv")[0]


def assembly_for_bgc(domain_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the ordered assembly line for one BGC's aSDomain rows."""
    seq = []
    for d in domain_rows:
        if d.get("feature_type") != "aSDomain":
            continue
        try:
            st = int(d.get("start") or 0)
        except Exception:
            st = 0
        seq.append((st, d.get("locus_tag", ""), d.get("domain", ""), (d.get("substrate") or "").strip()))
    seq.sort()
    monomers, extenders = [], []
    n_c = n_ks = te = epim = 0
    for st, loc, dm, sub in seq:
        dl = dm.lower()
        if "condensation" in dl:
            n_c += 1
        if dm == "PKS_KS" or "beta-ketoacyl" in dl:
            n_ks += 1
        if "thioesterase" in dl or dm == "TD":
            te += 1
        if "epimeriz" in dl:
            epim += 1
        if "amp-binding" in dl and sub and sub != "X":
            monomers.append(sub)
        if dm == "PKS_AT" and sub:
            extenders.append(sub)
    n_modules = max(n_c, len(monomers)) + max(0, n_ks)  # coarse lower bound
    ms = {m.lower() for m in monomers}
    cons = []
    if {"hpg", "dhpg"} & ms and len(monomers) >= 5:
        cons.append("GPA-aglycone-consistent (Hpg/dHpg heptapeptide)")
    if "orn" in ms and n_ks and len(monomers) <= 2:
        cons.append("PTM/HSAF-consistent (iterative PKS + single Orn-loading NRPS module)")
    if n_ks >= 6 and extenders and te:
        cons.append("modular-polyketide-consistent (macrolide/polyene: many KS modules + release TE)")
    if epim:
        cons.append(f"{epim} D-configured residue(s) (Epimerization)")
    return dict(monomers=monomers, extenders=extenders, n_c=n_c, n_ks=n_ks, te=te, epim=epim,
                n_modules=n_modules, class_consistency="; ".join(cons))


def assembly_line_str(a: dict[str, Any]) -> str:
    parts = []
    if a["monomers"]:
        parts.append("NRPS monomers " + "–".join(a["monomers"]) + f" ({len(a['monomers'])} A-domains)")
    if a["extenders"]:
        parts.append("PKS extenders " + "–".join(a["extenders"]) + f" ({len(a['extenders'])} AT)")
    if a["te"]:
        parts.append(f"TE×{a['te']} release")
    if a["epim"]:
        parts.append(f"Epim×{a['epim']} (D-residues)")
    body = "; ".join(parts) if parts else "no ordered A/AT substrate domains recovered"
    cc = f" -> {a['class_consistency']}" if a["class_consistency"] else ""
    return body + cc


def run(package_dir: str | os.PathLike, out_dir: str | os.PathLike | None = None) -> dict[str, Any]:
    """Emit per-BGC assembly lines for a sealed package. Writes ASSEMBLY_LINES/{strain}_assembly_lines.csv."""
    package_dir = str(package_dir)
    dpath = _find_domains_csv(package_dir)
    if not dpath:
        return {"status": "no_domains_csv",
                "note": "no *_domains.csv in package (pre-gene_context cut?); skipped", "bgcs": 0}
    strain = _strain_of(package_dir, dpath)
    outd = os.path.join(str(out_dir or package_dir), "ASSEMBLY_LINES")
    os.makedirs(outd, exist_ok=True)
    # v9.7.374 fix: was case-sensitive (same gap fixed for p450_tailoring.py at v9.7.371).
    # EXCLUDE_STRAINS (raw_analysis_excluded()) is canonical uppercase (e.g. "AS-XXX");
    # strain here comes from an arbitrary manifest.json string or a filename-derived
    # fallback, neither normalized. A differently-cased strain id silently bypassed this
    # whole-strain exclude gate and emitted assembly lines for a strain that
    # OFFICIAL_DATA/EXCLUSIONS.md policy says should produce none.
    if strain.strip().upper() in {s.upper() for s in EXCLUDE_STRAINS}:
        with open(os.path.join(outd, "EXCLUDED.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"strain {strain} on the whole-strain exclude list — no assembly lines emitted\n")
        return {"status": "excluded_strain", "strain": strain, "bgcs": 0}

    by_bgc: dict[str, list[dict]] = collections.defaultdict(list)
    with open(dpath, encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            by_bgc[d.get("bgc_id", "")].append(d)

    rows = []
    for bgc, drows in by_bgc.items():
        a = assembly_for_bgc(drows)
        if not (a["monomers"] or a["extenders"] or a["n_ks"] or a["n_c"]):
            continue  # no assembly line (e.g. bare terpene) — omit
        rows.append({"strain": strain, "bgc_id": bgc, "n_modules": a["n_modules"],
                     "n_KS": a["n_ks"], "n_C": a["n_c"], "TE": a["te"], "Epim": a["epim"],
                     "monomers": "–".join(a["monomers"]), "extenders": "–".join(a["extenders"]),
                     "class_consistency": a["class_consistency"],
                     "assembly_line": assembly_line_str(a)})

    cols = ["strain", "bgc_id", "n_modules", "n_KS", "n_C", "TE", "Epim", "monomers", "extenders",
            "class_consistency", "assembly_line"]
    out = os.path.join(outd, f"{strain}_assembly_lines.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        fh.write(CLAIM_HEADER + "\n")
        w = _SafeDictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda x: (-x["n_modules"], x["bgc_id"])):
            w.writerow(r)

    consistent = sum(1 for r in rows if r["class_consistency"])
    return {"status": "ok", "strain": strain, "bgcs": len(rows), "class_consistent": consistent,
            "out": out}


def assembly_line_command(args) -> int:
    res = run(args.package, getattr(args, "out", None))
    emit(f"assembly-line: {res.get('status')} | strain={res.get('strain','?')} | "
          f"BGCs with an assembly line={res.get('bgcs', 0)}")
    if res.get("status") == "ok":
        emit(f"  class-consistent reads: {res['class_consistent']}")
        emit("  ->", res["out"])
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Predicted PKS/NRPS assembly-line report over a sealed package")
    ap.add_argument("package", help="path to a sealed package directory (must contain *_domains.csv)")
    ap.add_argument("--out", default=None, help="output root (default: the package dir)")
    a = ap.parse_args()
    raise SystemExit(assembly_line_command(a))
