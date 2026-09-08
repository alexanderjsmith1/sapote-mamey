"""p450_tailoring.py — cytochrome-P450 oxidative-tailoring classifier (roadmap #11).

FREEZE-SAFE ADDITIVE REPORT LAYER. Reads a *already-sealed* package's per-gene table
(``*_gene_by_gene_all_bgcs.csv``), flags cytochrome-P450 genes (p450 / PF00067 /
SMCOG1007 tokens in the sec_met / product qualifier), counts them per BGC, and assigns
each P450 a **class-level role prior**:

  * ``crosslinker-candidate``  — a BGC carrying **>=3 clustered P450s** (the oxidative-
    crosslinking cassette signature of glycopeptide-type / complex oxidative maturation).
    Sharpened to ``crosslinker-candidate (GPA)`` only when the BGC also shows glycopeptide
    context (NRPS scaffold + a Dpg/Hpg/vanHAX/X-domain token) — otherwise it reads as
    complex oxidative maturation on whatever scaffold is present (e.g. a lanthipeptide,
    NOT a glycopeptide — a real cohort P450-cassette lesson [Redacted — publication in preparation]).
  * ``oxidative-tailoring``    — hydroxylase / epoxidase / oxidase decoration prior for
    every other P450.

Writes a per-gene ``P450_INVENTORY.tsv`` + a per-BGC rollup + a short memo into a
``P450_TAILORING/`` subfolder. Touches NO scan/scorer/tier/gate — re-run yields identical
triage. Non-blocking, like render-figures.

CLAIM CEILING (mandatory): a P450's role prior is a class-level inference from clustering +
scaffold context, NOT a proven catalytic activity, and NEVER a product/structure/bioactivity
claim. Judgment deferred.
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

# SSOT: raw-data module -> raw_analysis_excluded() = {AS-XXX, AS-XXX}. See OFFICIAL_DATA/EXCLUSIONS.md.
from .exclusions import raw_analysis_excluded
EXCLUDE_STRAINS = raw_analysis_excluded()
CROSSLINK_CASSETTE_MIN = 3  # >= this many P450s in one BGC == oxidative-crosslinking cassette

CLAIM_HEADER = (
    "# P450-tailoring report (freeze-safe additive layer). role_prior (crosslinker-candidate vs "
    "oxidative-tailoring) is a class-level inference from P450 clustering + scaffold context, NOT a "
    "proven catalytic activity and NEVER a product/structure/bioactivity claim. Judgment deferred."
)

# glycopeptide-crosslinking context tokens in the gene table (secondary confirmation when present).
# NOTE: the gene-by-gene table usually does NOT carry Dpg/Hpg/vanHAX names — the glycopeptide signal
# lives in the KCB anchor (e.g. balhimycin) + the domain-reference X-domain flag. So the PRIMARY GPA
# sharpener is the triage-board anchor (see _GPA_ANCHOR_TOKENS); gene tokens only add confidence.
_GPA_GENE_TOKENS = ("vanhax", "vanh ", "x-domain", "x_domain", "glycopeptide", "oxya", "oxyb", "oxyc")

# GPA (and GPA-relative) KCB/MIBiG anchor names — the in-package signal that a >=3-P450 cassette is
# specifically a glycopeptide crosslinking cassette rather than generic complex oxidative maturation.
_GPA_ANCHOR_TOKENS = ("vancomycin", "teicoplanin", "balhimycin", "chloroeremomycin", "a47934",
                      "a40926", "ristocetin", "kistamicin", "complestatin", "corbomycin",
                      "keratinimicin", "pekiskomycin", "feglymycin", "gp6738", "uk-68",
                      "enduracidin", "ramoplanin", "enduracididine")


def _is_p450(*fields: str) -> bool:
    blob = " ".join(f or "" for f in fields).lower()
    return ("p450" in blob) or ("pf00067" in blob) or ("smcog1007" in blob)


def _scaffold_of(products: str) -> str:
    """Coarse scaffold class from a BGC's antiSMASH product string (for role context, not a claim)."""
    p = (products or "").lower()
    has = lambda *ts: any(t in p for t in ts)
    tags = []
    if has("nrps"):
        tags.append("NRPS")
    if has("pks", "t1pks", "t2pks", "t3pks", "transatpks", "hglks"):
        tags.append("PKS")
    if has("terpene"):
        tags.append("terpene")
    if has("lanthipeptide", "lassopeptide", "ripp", "thiopeptide", "sactipeptide",
           "lap", "bacteriocin", "redox_cofactor"):
        tags.append("RiPP")
    if has("siderophore", "nrp-metallophore"):
        tags.append("siderophore")
    return "+".join(tags) if tags else (products.split(";")[0].strip() if products else "unknown")


def _find_gene_table(package_dir: str | os.PathLike) -> str | None:
    hits = sorted(glob.glob(os.path.join(str(package_dir), "*_gene_by_gene_all_bgcs.csv")))
    return hits[0] if hits else None


def _gpa_anchor_bgcs(package_dir: str) -> set[str]:
    """BGC ids whose triage-board KCB anchor is a glycopeptide (or GPA-relative) — the in-package
    signal that a P450 cassette is specifically a GPA crosslinking cassette. Empty if no board."""
    hits = sorted(glob.glob(os.path.join(package_dir, "*_4_triage_board.csv")))
    if not hits:
        return set()
    out: set[str] = set()
    with open(hits[0], encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            kcb = (d.get("KCB_top", "") or "").lower()
            if any(t in kcb for t in _GPA_ANCHOR_TOKENS):
                out.add(d.get("BGC_ID", ""))
    return out


def _strain_of(package_dir: str, table: str) -> str:
    mp = os.path.join(package_dir, "manifest.json")
    if os.path.exists(mp):
        try:
            m = json.loads(Path(mp).read_text(encoding="utf-8"))
            for k in ("strain", "strain_id", "Strain"):
                if m.get(k):
                    return str(m[k])
        except Exception:
            pass
    return os.path.basename(table).split("_gene_by_gene_all_bgcs")[0]


def run(package_dir: str | os.PathLike, out_dir: str | os.PathLike | None = None) -> dict[str, Any]:
    """Classify a sealed package's P450 genes into oxidative-tailoring vs crosslinker cassettes.
    Writes P450_INVENTORY.tsv + P450_BY_BGC.tsv + P450_MEMO.md into <out_dir>/P450_TAILORING/."""
    package_dir = str(package_dir)
    table = _find_gene_table(package_dir)
    if not table:
        return {"status": "no_gene_table", "note": "no *_gene_by_gene_all_bgcs.csv in package; skipped",
                "p450_genes": 0}
    strain = _strain_of(package_dir, table)
    outd = os.path.join(str(out_dir or package_dir), "P450_TAILORING")
    os.makedirs(outd, exist_ok=True)
    # v9.7.371 fix: was case-sensitive. EXCLUDE_STRAINS (raw_analysis_excluded()) is canonical
    # uppercase (e.g. "AS-XXX"); strain here comes from an arbitrary manifest.json string or a
    # filename-derived fallback, neither normalized. A differently-cased strain id silently
    # bypassed this whole-strain exclude gate and emitted a full P450 inventory for a strain that
    # OFFICIAL_DATA/EXCLUSIONS.md policy says should produce none.
    if strain.strip().upper() in {s.upper() for s in EXCLUDE_STRAINS}:
        note = f"strain {strain} is on the whole-strain exclude list — no P450 inventory emitted"
        _excl_path = os.path.join(outd, "EXCLUDED.txt")
        _excl_tmp = _excl_path + ".tmp"
        with open(_excl_tmp, "w", encoding="utf-8") as fh:
            fh.write(note + "\n")
        os.replace(_excl_tmp, _excl_path)
        return {"status": "excluded_strain", "strain": strain, "note": note, "p450_genes": 0}

    gpa_anchor_bgcs = _gpa_anchor_bgcs(package_dir)  # primary GPA signal: glycopeptide KCB anchor

    # pass 1: collect P450 genes + per-BGC scaffold/context
    p450: list[dict[str, Any]] = []
    per_bgc_ctx: dict[str, dict[str, Any]] = {}
    with open(table, encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            bgc = d.get("bgc_id", "")
            secmet = d.get("sec_met_domains", "")
            prodq = d.get("product_qualifier", "")
            func = d.get("gene_function_inference", "")
            bctx = per_bgc_ctx.setdefault(bgc, {"products": d.get("bgc_products", ""),
                                                "gpa_ctx": bgc in gpa_anchor_bgcs,
                                                "af": d.get("af_score", ""), "ab": d.get("ab_score", "")})
            blob = " ".join((secmet, prodq, func)).lower()
            if any(t in blob for t in _GPA_GENE_TOKENS):
                bctx["gpa_ctx"] = True
            if _is_p450(secmet, prodq, func):
                p450.append(dict(strain=strain, bgc_id=bgc, locus_tag=d.get("locus_tag", ""),
                                 cds_start=d.get("cds_start", ""), cds_end=d.get("cds_end", ""),
                                 sec_met=secmet[:120], bgc_products=d.get("bgc_products", ""),
                                 af=d.get("af_score", ""), ab=d.get("ab_score", "")))

    # per-BGC P450 counts
    counts = collections.Counter(g["bgc_id"] for g in p450)

    def role_and_note(bgc: str) -> tuple[str, str]:
        n = counts[bgc]
        scaffold = _scaffold_of(per_bgc_ctx.get(bgc, {}).get("products", ""))
        if n >= CROSSLINK_CASSETTE_MIN:
            gpa = per_bgc_ctx.get(bgc, {}).get("gpa_ctx", False) and "NRPS" in scaffold
            if gpa:
                return ("crosslinker-candidate (GPA)",
                        f"{n} clustered P450 + glycopeptide context (GPA KCB anchor / Dpg/Hpg/vanHAX/"
                        f"X-domain) on {scaffold}")
            return ("crosslinker-candidate",
                    f"{n} clustered P450 (complex oxidative-maturation cassette) on {scaffold}; "
                    f"no glycopeptide context -> NOT a GPA call")
        return ("oxidative-tailoring",
                f"hydroxylase/epoxidase/oxidase decoration prior on {scaffold} ({n} P450 in BGC)")

    for g in p450:
        r, note = role_and_note(g["bgc_id"])
        g["p450_count_in_bgc"] = counts[g["bgc_id"]]
        g["role_prior"] = r
        g["role_note"] = note

    # per-gene inventory
    cols = ["strain", "bgc_id", "locus_tag", "p450_count_in_bgc", "role_prior", "role_note",
            "bgc_products", "af", "ab", "cds_start", "cds_end", "sec_met"]
    _inv_path = os.path.join(outd, "P450_INVENTORY.tsv")
    _inv_tmp = _inv_path + ".tmp"
    with open(_inv_tmp, "w", newline="", encoding="utf-8") as fh:
        fh.write(CLAIM_HEADER + "\n")
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for g in sorted(p450, key=lambda x: (-x["p450_count_in_bgc"], x["bgc_id"], x["locus_tag"])):
            w.writerow(g)
    os.replace(_inv_tmp, _inv_path)

    # per-BGC rollup
    bgc_rows = []
    for bgc, n in counts.most_common():
        r, note = role_and_note(bgc)
        bgc_rows.append({"strain": strain, "bgc_id": bgc, "n_p450": n, "role_prior": r,
                         "scaffold": _scaffold_of(per_bgc_ctx.get(bgc, {}).get("products", "")),
                         "af": per_bgc_ctx.get(bgc, {}).get("af", ""),
                         "ab": per_bgc_ctx.get(bgc, {}).get("ab", ""), "note": note})
    _bybgc_path = os.path.join(outd, "P450_BY_BGC.tsv")
    _bybgc_tmp = _bybgc_path + ".tmp"
    with open(_bybgc_tmp, "w", newline="", encoding="utf-8") as fh:
        fh.write(CLAIM_HEADER + "\n")
        w = _SafeDictWriter(fh, fieldnames=["strain", "bgc_id", "n_p450", "role_prior", "scaffold",
                                           "af", "ab", "note"], delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in bgc_rows:
            w.writerow(r)
    os.replace(_bybgc_tmp, _bybgc_path)

    n_cross = sum(1 for g in p450 if g["role_prior"].startswith("crosslinker"))
    cassettes = [r for r in bgc_rows if r["n_p450"] >= CROSSLINK_CASSETTE_MIN]
    _memo_path = os.path.join(outd, "P450_MEMO.md")
    _memo_tmp = _memo_path + ".tmp"
    with open(_memo_tmp, "w", encoding="utf-8") as fh:
        fh.write(f"# Cytochrome-P450 tailoring report — {strain}\n\n")
        fh.write(f"**{len(p450)} P450 genes across {len(counts)} BGCs.** "
                 f"{n_cross} crosslinker-candidate / {len(p450)-n_cross} oxidative-tailoring priors.\n\n")
        fh.write("> " + CLAIM_HEADER.lstrip("# ") + "\n\n")
        if cassettes:
            fh.write(f"## Crosslinking-cassette candidates (>={CROSSLINK_CASSETTE_MIN} clustered P450)\n\n")
            fh.write("| BGC | #P450 | role_prior | scaffold | note |\n|---|---|---|---|---|\n")
            for r in cassettes:
                fh.write(f"| {r['bgc_id']} | {r['n_p450']} | {r['role_prior']} | {r['scaffold']} | {r['note']} |\n")
        else:
            fh.write("No >=3-clustered-P450 crosslinking cassettes in this strain.\n")
    os.replace(_memo_tmp, _memo_path)

    return {"status": "ok", "strain": strain, "p450_genes": len(p450), "bgcs_with_p450": len(counts),
            "crosslinker_candidates": n_cross, "cassette_bgcs": len(cassettes), "out_dir": outd}


def p450_tailoring_command(args) -> int:
    res = run(args.package, getattr(args, "out", None))
    emit(f"p450-tailoring: {res.get('status')} | strain={res.get('strain','?')} | "
          f"P450 genes={res.get('p450_genes', 0)} in {res.get('bgcs_with_p450', 0)} BGCs")
    if res.get("status") == "ok":
        emit(f"  crosslinker-candidates={res['crosslinker_candidates']} "
              f"({res['cassette_bgcs']} cassette BGCs)")
        emit("  ->", res["out_dir"])
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Cytochrome-P450 tailoring report over a sealed package")
    ap.add_argument("package", help="path to a sealed package directory")
    ap.add_argument("--out", default=None, help="output root (default: the package dir)")
    a = ap.parse_args()
    raise SystemExit(p450_tailoring_command(a))
