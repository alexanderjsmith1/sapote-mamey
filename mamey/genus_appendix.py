#!/usr/bin/env python3
"""mamey genus-appendix — antifungal (AF) & antibacterial (AB) candidate appendices, by genus.

Read-only cohort reporting. Scans sealed Mamey packages, groups BGCs by genus (from each
manifest's taxonomy), and flags per-BGC AF / AB *candidate* rows by keyword match over the
antiSMASH product class and the top KnownClusterBlast comparator. Emits one Markdown appendix
per activity family, grouped by genus.

Claim safety: a flag means a comparator/class keyword matched — it is a **capacity-level,
class-level hypothesis about the comparator family, NOT a claim that the strain produces the
compound or has the activity**. AF is the primary discovery target; AB (e.g. MRSA / foulbrood)
is secondary. Nothing here is a bioactivity or structural claim; wet-lab evidence is required.

Usage:
    python mamey_run.py genus-appendix [ROOT] [--out DIR] [--depth N]
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

import argparse
import csv
import json
import re
from pathlib import Path

# Keyword sets are comparator-family markers, deliberately explicit and auditable.
AF_KEYWORDS = (
    "antifungal", "polyene", "amphotericin", "nystatin", "candicidin", "filipin",
    "pimaricin", "natamycin", "rimocidin", "tetramycin", "azole", "echinocandin",
    "pneumocandin", "nikkomycin", "polyoxin", "aureobasidin", "griseofulvin",
    "strobilurin", "chitin synthase", "faeriefungin", "guadinomine",
)
AB_KEYWORDS = (
    "antibacterial", "glycopeptide", "vancomycin", "teicoplanin", "beta-lactam",
    "penicillin", "cephalosporin", "aminoglycoside", "streptomycin", "kanamycin",
    "macrolide", "erythromycin", "tetracycline", "actinomycin", "rifamycin",
    "ansamycin", "daptomycin", "streptothricin", "chloramphenicol", "novobiocin",
    "bacitracin", "streptophenazine", "phenazine",
)
CLAIM_SAFETY = (
    "Candidate flags are comparator/class keyword matches — capacity-level, class-level "
    "hypotheses about the comparator family, NOT claims of production, activity, novelty, or "
    "structure. Wet-lab evidence required."
)


def _genus_of(taxonomy: str) -> str:
    tax = (taxonomy or "").strip()
    if not tax:
        return "Unknown"
    first = tax.split()[0]
    return first if first[:1].isupper() else "Unknown"


# v9.7.374 fix: the bare "azole" AF keyword (unbounded substring match, like every other keyword
# in AF_KEYWORDS/AB_KEYWORDS) false-matched "thiazole"/"oxazole" -- common RiPP/LAP heterocycle
# terminology (goadsporin, microcins, bottromycin-class thiazole/oxazole-modified peptides; LAP =
# "linear azol(in)e-containing peptide" is literally named for this chemistry), unrelated to azole
# ANTIFUNGAL drugs (fluconazole/itraconazole/voriconazole-class triazoles/imidazoles). A negative
# lookbehind excludes only the "thi"/"ox" prefixes (thiazole/oxazole/benzoxazole) while still
# matching every genuine azole-antifungal-class term (triazole, imidazole, -conazole compounds,
# bare "azole").
_AZOLE_NOT_THIAZOLE_OXAZOLE_RE = re.compile(r"(?<!thi)(?<!ox)azole")


def _match(text: str, keywords) -> list[str]:
    low = (text or "").lower()
    hits = []
    for k in keywords:
        if k == "azole":
            if _AZOLE_NOT_THIAZOLE_OXAZOLE_RE.search(low):
                hits.append(k)
        elif k in low:
            hits.append(k)
    return hits


def _scan_package(pkg_dir: Path) -> list[dict]:
    """Return per-BGC candidate rows for one sealed package (empty if not a package)."""
    manifest = pkg_dir / "manifest.json"
    if not manifest.is_file():
        return []
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return []
    strain = str(m.get("strain_id") or pkg_dir.name)
    genus = _genus_of(str(m.get("taxonomy") or ""))
    release = str(m.get("release") or "")
    inv = next(iter(pkg_dir.glob("*_2_inventory.csv")), None)
    if inv is None:
        return []
    rows: list[dict] = []
    try:
        with inv.open(newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                products = r.get("Products", "") or ""
                comparator = r.get("KCB_top", "") or ""
                hay = f"{products} {comparator}"
                af = _match(hay, AF_KEYWORDS)
                ab = _match(hay, AB_KEYWORDS)
                if not af and not ab:
                    continue
                rows.append({
                    "genus": genus, "strain": strain, "release": release,
                    "bgc_id": r.get("BGC_ID", ""), "products": products,
                    "comparator": comparator, "boundary": r.get("Boundary", ""),
                    "af_basis": ";".join(af), "ab_basis": ";".join(ab),
                })
    except Exception:
        return rows
    return rows


def _find_packages(root: Path, depth: int) -> list[Path]:
    out = []
    root = Path(root)
    if (root / "manifest.json").is_file():
        return [root]
    for p in root.rglob("manifest.json"):
        rel_depth = len(p.relative_to(root).parts)
        if rel_depth <= depth + 1:
            out.append(p.parent)
    return sorted(set(out))


def _render(family: str, keyword_field: str, rows: list[dict]) -> str:
    hits = [r for r in rows if r[keyword_field]]
    by_genus: dict[str, list[dict]] = {}
    for r in hits:
        by_genus.setdefault(r["genus"], []).append(r)
    L = [f"# {family} candidate appendix — by genus", "",
         f"> {CLAIM_SAFETY}", "",
         f"**{len(hits)} candidate BGC rows across {len(by_genus)} genera "
         f"({len({r['strain'] for r in hits})} strains).**", ""]
    for genus in sorted(by_genus):
        grp = by_genus[genus]
        L += [f"## {genus}  ({len(grp)} candidate rows)", "",
              "| Strain | BGC | antiSMASH class | Comparator (KCB) | Boundary | Basis |",
              "|---|---|---|---|---|---|"]
        for r in sorted(grp, key=lambda x: (x["strain"], x["bgc_id"])):
            L.append(f"| {r['strain']} | {r['bgc_id']} | {r['products']} | "
                     f"{r['comparator']} | {r['boundary']} | {r[keyword_field]} |")
        L.append("")
    return "\n".join(L) + "\n"


def run(root: str | Path = ".", out_dir: str | Path | None = None, depth: int = 3) -> dict:
    root = Path(root)
    pkgs = _find_packages(root, depth)
    rows: list[dict] = []
    for pkg in pkgs:
        rows.extend(_scan_package(pkg))
    af_md = _render("Antifungal (AF)", "af_basis", rows)
    ab_md = _render("Antibacterial (AB)", "ab_basis", rows)
    result = {
        "packages": len(pkgs),
        "af_candidate_rows": sum(1 for r in rows if r["af_basis"]),
        "ab_candidate_rows": sum(1 for r in rows if r["ab_basis"]),
        "af_markdown": af_md, "ab_markdown": ab_md,
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "GENUS_ANTIFUNGAL_APPENDIX.md").write_text(af_md, encoding="utf-8")
        (out / "GENUS_ANTIBACTERIAL_APPENDIX.md").write_text(ab_md, encoding="utf-8")
        result["out_dir"] = str(out)
    return result


def genus_appendix_command(args) -> int:
    res = run(getattr(args, "root", ".") or ".",
              out_dir=getattr(args, "out", None),
              depth=getattr(args, "depth", 3))
    if res.get("out_dir"):
        emit(f"genus-appendix: {res['packages']} packages -> "
              f"{res['af_candidate_rows']} AF + {res['ab_candidate_rows']} AB candidate rows "
              f"written to {res['out_dir']}")
    else:
        emit(res["af_markdown"], res["ab_markdown"], sep="\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="AF/AB candidate appendices by genus")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--out")
    ap.add_argument("--depth", type=int, default=3)
    return genus_appendix_command(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
