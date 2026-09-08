"""mamey.class_believability — committed-step believability engine (LQ-PATH-01).

Judges the *believability* of a biosynthetic class call from its enzyme logic, not from the
antiSMASH class label alone. antiSMASH fires a class rule (and Mamey a CCTT trigger) on a single
diagnostic hit, but many classes have a hard *committed step* whose gateway Pfam is degenerate, so
the label over-calls. This engine encodes each class the way a reviewer reads a cluster —
*necessary gateway → committed pull → warhead/tailoring → assembly*, plus the named false-positive
superfamily that makes the label over-call — and returns a tiered call with the evidence.

    HIGH    : gateway (good hit) + committed pull + >=1 downstream (tailoring/TIGR/assembly).
    MEDIUM  : gateway (good hit) + partial corroboration (committed pull OR >=2 associated markers).
    LOW     : gateway only / weak, no committed pull, <=1 associated marker -> named-FP risk.
    SUSPECT : class flagged by antiSMASH/CCTT but NO gateway enzyme captured.
    NONE    : neither gateway nor class flag -> not a candidate for this class.

Boundary/assembly status is CONTEXT, never a demotion (fragment-surfacing principle): a real gateway
on a contig edge is still a real gateway.

TWO PASSES (RFC LQ-PATH-01 1b):
  * LOCAL  (per-BGC): does *this region* carry the committed-step set?
  * POOLED (per-strain): union every CDS across all regions/contigs and ask whether the strain,
    *anywhere*, has the full set for the class — even if split across fragments. When the pooled tier
    is stronger than the best single-BGC tier, that is a **candidate split pathway** (cross-reference
    RG-GMCI 4A_*): the best gene in a strain can be an orphan the BGC-local view rates LOW.

Reads only post-seal artifacts (`*_gene_context.jsonl` + `_2_inventory.csv`), so this runs as a
non-blocking post-seal subcommand and never touches `run_one_strain` or any gate.

The phosphonate module is validated (ran across the AS + SID cohorts; matches the Lab Quest
`pathway_logic/phosphonate_logic.py` prototype). Other classes are added as small registry entries;
only validated modules are shipped so the engine never manufactures a believability it can't defend.

CLI:
    python mamey_run.py class-believability <package_dir> [<package_dir> ...] \
        [--class phosphonate] [--json out.json] [--csv out.csv]
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
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

WEAK_GATEWAY_BIT = 60.0  # a gateway hit below this bitscore is "weak" (named-FP risk)
RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "SUSPECT": 3, "NONE": 4}
_TIER_ORDER = ["HIGH", "MEDIUM", "LOW", "SUSPECT"]


@dataclass(frozen=True)
class ClassModule:
    """One class's committed-step logic. All patterns match case-insensitively against a BGC's
    union of sec_met_domains + antiSMASH product/gene_functions text."""
    name: str
    gateway: tuple[str, ...]          # necessary gateway enzyme(s); no gateway -> not de-novo biosynthesis
    committed: tuple[str, ...]        # committed pull (traps a reversible/unfavourable gateway step)
    tigr: tuple[str, ...]             # class-diagnostic TIGRFAMs / named tailoring markers
    warhead: tuple[str, ...]          # warhead/tailoring enzymes (counted)
    assembly: tuple[str, ...]         # assembly-line markers (ligase / NRPS / PKS)
    engine_flag: tuple[str, ...]      # antiSMASH/CCTT class tokens (drives SUSPECT when gateway absent)
    fp_superfamily: str               # the named false-positive superfamily the label over-calls into
    gateway_bit_re: re.Pattern = field(default=None)  # optional: extract the gateway bitscore for weak-hit test


# --- phosphonate (validated; mirrors Lab Quest pathway_logic/phosphonate_logic.py) ----------------
# PEP --(PEP mutase, PepM)--> phosphonopyruvate --(Ppd, TPP decarboxylase)--> phosphonoacetaldehyde
#     --(aminotransferase / AA-kinase)--> amino-phosphonate warhead --(ATP-grasp / NRPS)--> phospho-PEPTIDE
PHOSPHONATE = ClassModule(
    name="phosphonate",
    gateway=("pep_mutase", "carboxyvinyl-carboxyphosphonate", "smcog1231",
             "phosphoenolpyruvate mutase", "phosphonopyruvate"),
    committed=("tpp_enzyme",),  # phosphonopyruvate decarboxylase (traps the reversible PepM step)
    tigr=("tigr03944", "tigr03945", "tigr03335", "phna", "phosphonatase",
          "phosphonoacet", "aminoethylphosphon"),
    warhead=("aminotran", "aa_kinase", "metallophos", "palp", "ntp_transf", "ocd_mu_crystall"),
    assembly=("atp-grasp", "atpgrasp", "amp-binding", "condensation", "nrps"),
    engine_flag=("phosphonate", "phosphonates", "t43-pho"),
    fp_superfamily="isocitrate-lyase superfamily (carboxyPEP mutase / methylisocitrate lyase — primary metabolism)",
    gateway_bit_re=re.compile(r"PEP_mutase[^)]*bitscore:\s*([\d.]+)", re.I),
)

# Registry of shipped, validated modules. Add a module here to extend the engine (RFC proposes
# polyene / enediyne / RiPP-maturation next); only ship a class once its committed-step logic is
# validated against a cohort, so a believability tier is never manufactured.
REGISTRY: dict[str, ClassModule] = {PHOSPHONATE.name: PHOSPHONATE}


def _hit(blob: str, patterns) -> bool:
    return any(p in blob for p in patterns)


def scan_bgc(cds_list: list[dict], mod: ClassModule) -> dict:
    """Compute the marker profile for one CDS list (a BGC, or a pooled strain) under `mod`."""
    domains: set[str] = set()
    blob_parts: list[str] = []
    gateway_loci: list[str] = []
    marker_loci: dict[str, list[str]] = {}
    for c in cds_list:
        for d in (c.get("sec_met_domains") or []):
            domains.add(str(d))
        gf = " ".join(str(c.get(k, "")) for k in ("product", "gene_functions"))
        blob_parts.append(gf)
        low = (gf + " " + " ".join(str(d) for d in (c.get("sec_met_domains") or []))).lower()
        lt = c.get("locus_tag", "?")
        if _hit(low, mod.gateway):
            gateway_loci.append(lt)
        for tier_name, pats in (("committed", mod.committed), ("tigr", mod.tigr),
                                ("warhead", mod.warhead), ("assembly", mod.assembly)):
            if _hit(low, pats):
                marker_loci.setdefault(tier_name, []).append(lt)
    blob = " ".join(blob_parts).lower()
    dom_blob = " ".join(domains).lower() + " " + blob
    bit = None
    if mod.gateway_bit_re is not None:
        bits = [float(x) for x in mod.gateway_bit_re.findall(" ".join(blob_parts))]
        bit = max(bits) if bits else None
    return {
        "gateway": bool(gateway_loci),
        "gateway_loci": gateway_loci,
        "gateway_bitscore": bit,
        "committed": _hit(dom_blob, mod.committed),
        "tigr": _hit(dom_blob, mod.tigr),
        "warhead_count": sum(1 for p in mod.warhead if p in dom_blob),
        "assembly": _hit(dom_blob, mod.assembly),
        "engine_flag": _hit(dom_blob, mod.engine_flag),
        "marker_loci": marker_loci,
        "n_cds": len(cds_list),
    }


def classify(m: dict, mod: ClassModule) -> tuple[str, str]:
    """Uniform committed-step tier logic (parameterised by the module)."""
    G, bit = m["gateway"], m["gateway_bitscore"]
    D, T, W, A = m["committed"], m["tigr"], m["warhead_count"], m["assembly"]
    weak = (bit is not None and bit < WEAK_GATEWAY_BIT)
    if not G:
        if m["engine_flag"]:
            return "SUSPECT", (f"{mod.name} called by antiSMASH/CCTT but NO gateway enzyme captured "
                               f"— not believable as de-novo {mod.name} biosynthesis (class trigger "
                               f"without the committed step)")
        return "NONE", f"no {mod.name} gateway or class flag"
    downstream = (T or W >= 1 or A)
    if D and downstream and not weak:
        return "HIGH", (f"{mod.name}: gateway + committed pull + downstream marker(s) — canonical "
                        f"committed signature with tailoring/assembly")
    if (D or T or W >= 2) and not weak:
        return "MEDIUM", (f"{mod.name}: gateway + partial corroboration (committed pull or >=2 "
                          f"associated markers) — believable capacity, signature incomplete")
    return "LOW", (f"{mod.name}: gateway only" + (" (weak hit)" if weak else "") +
                   f", no committed pull and <=1 associated marker — verify gateway identity; also "
                   f"hits the {mod.fp_superfamily}, a known false positive")


def _inventory_index(pkg: Path, strain: str) -> dict:
    idx = {}
    inv = pkg / f"{strain}_2_inventory.csv"
    if inv.exists():
        with open(inv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                idx[r.get("BGC_ID")] = r
    return idx


def _load_bgcs(pkg: Path) -> list[dict]:
    """Load [{bgc_id, cds:[...]}] from the sealed package's *_gene_context.jsonl."""
    jsonl = next(pkg.glob("*_gene_context.jsonl"), None)
    if not jsonl:
        return []
    out = []
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and "cds" in rec and "bgc_id" in rec:
                out.append(rec)
    return out


def scan_package(pkg: Path, mod: ClassModule) -> dict:
    """Run the LOCAL (per-BGC) and POOLED (per-strain) passes for one package and one class."""
    strain = pkg.parent.name
    bgcs = _load_bgcs(pkg)
    inv = _inventory_index(pkg, strain)

    local_rows: list[dict] = []
    for rec in bgcs:
        m = scan_bgc(rec["cds"], mod)
        if not m["gateway"] and not m["engine_flag"]:
            continue  # not a candidate for this class
        tier, reason = classify(m, mod)
        if tier == "NONE":
            continue
        row = inv.get(rec["bgc_id"], {})
        local_rows.append({
            "strain": strain, "bgc_id": rec["bgc_id"], "cls": mod.name, "scope": "local",
            "believability": tier, "reason": reason,
            "gateway": m["gateway"], "gateway_bitscore": m["gateway_bitscore"],
            "committed": m["committed"], "tigr": m["tigr"], "warhead_count": m["warhead_count"],
            "assembly": m["assembly"],
            "products": row.get("Products", ""), "boundary": row.get("Boundary", ""),
            "length_kb": row.get("Length_kb", ""), "kcb_top": row.get("KCB_top", ""),
            "contig": row.get("Contig", ""), "gateway_loci": ";".join(m["gateway_loci"]),
            "n_cds": m["n_cds"],
        })
    local_rows.sort(key=lambda r: (RANK[r["believability"]], r["bgc_id"]))

    # POOLED per-strain pass: union all CDS across every region.
    pooled_row = None
    all_cds = [c for rec in bgcs for c in rec["cds"]]
    if all_cds:
        mp = scan_bgc(all_cds, mod)
        if mp["gateway"] or mp["engine_flag"]:
            ptier, preason = classify(mp, mod)
            if ptier != "NONE":
                best_local = min((RANK[r["believability"]] for r in local_rows), default=RANK["NONE"])
                split = RANK[ptier] < best_local  # strain-level stronger than any single BGC
                pooled_row = {
                    "strain": strain, "bgc_id": "(pooled)", "cls": mod.name, "scope": "pooled",
                    "believability": ptier, "reason": preason,
                    "gateway": mp["gateway"], "gateway_bitscore": mp["gateway_bitscore"],
                    "committed": mp["committed"], "tigr": mp["tigr"],
                    "warhead_count": mp["warhead_count"], "assembly": mp["assembly"],
                    "split_pathway_candidate": split,
                    "gateway_loci": ";".join(mp["gateway_loci"]),
                    "marker_loci": {k: sorted(set(v)) for k, v in mp["marker_loci"].items()},
                    "n_cds": mp["n_cds"],
                }
    return {"strain": strain, "cls": mod.name, "local": local_rows, "pooled": pooled_row}


def build_report(package_dirs, classes=None) -> dict:
    """Run the engine over many packages for one or more classes; returns rows + counts."""
    mods = [REGISTRY[c] for c in (classes or list(REGISTRY))]
    local_all: list[dict] = []
    pooled_all: list[dict] = []
    for p in package_dirs:
        pkg = Path(p)
        for mod in mods:
            res = scan_package(pkg, mod)
            local_all.extend(res["local"])
            if res["pooled"]:
                pooled_all.append(res["pooled"])
    local_all.sort(key=lambda r: (r["cls"], RANK[r["believability"]], r["strain"], r["bgc_id"]))
    pooled_all.sort(key=lambda r: (r["cls"], RANK[r["believability"]], r["strain"]))
    counts: dict[str, dict[str, int]] = {}
    for r in local_all:
        counts.setdefault(r["cls"], {}).setdefault(r["believability"], 0)
        counts[r["cls"]][r["believability"]] += 1
    return {"classes": [m.name for m in mods], "counts": counts,
            "local": local_all, "pooled": pooled_all}


def register_subparser(sub):
    """Register the `class-believability` post-seal subcommand (called from cli.py)."""
    cb = sub.add_parser("class-believability",
                        help="committed-step class believability (HIGH/MEDIUM/LOW/SUSPECT) per BGC "
                             "and pooled per strain; non-blocking, reads a sealed package")
    cb.add_argument("packages", nargs="+", help="sealed package dir(s)")
    cb.add_argument("--class", dest="classes", action="append",
                    choices=sorted(REGISTRY), help="limit to class(es) (default: all shipped)")
    cb.add_argument("--json", dest="json_out", default=None, help="write full JSON report here")
    cb.add_argument("--csv", dest="csv_out", default=None, help="write the local (per-BGC) rows here")
    cb.set_defaults(func=run_from_args)
    return cb


def run_from_args(args) -> int:
    rep = build_report(args.packages, args.classes)
    for cls in rep["classes"]:
        c = rep["counts"].get(cls, {})
        n_split = sum(1 for r in rep["pooled"]
                      if r["cls"] == cls and r.get("split_pathway_candidate"))
        emit(f"[{cls}] " + " ".join(f"{t}={c.get(t, 0)}" for t in _TIER_ORDER) +
              f"  | pooled split-pathway candidates: {n_split}")
    if getattr(args, "json_out", None):
        Path(args.json_out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
        emit(f"  json -> {args.json_out}")
    if getattr(args, "csv_out", None):
        cols = ["strain", "bgc_id", "cls", "believability", "gateway", "gateway_bitscore",
                "committed", "tigr", "warhead_count", "assembly", "products", "boundary",
                "length_kb", "kcb_top", "gateway_loci", "reason"]
        with open(args.csv_out, "w", newline="", encoding="utf-8") as f:
            w = _SafeDictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rep["local"])
        emit(f"  csv  -> {args.csv_out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("packages", nargs="+", help="sealed package dir(s)")
    ap.add_argument("--class", dest="classes", action="append", choices=sorted(REGISTRY))
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--csv", dest="csv_out", default=None)
    return run_from_args(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
