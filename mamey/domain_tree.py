#!/usr/bin/env python3
"""domain_tree.py — the GATED builder pipeline for BGC-machinery domain trees (VGP-399, card 1/3).

`ks_phylogeny.extract_module_core_domains()` produces the reproducible INPUT to a domain tree; until
now the actual align→infer→gate→render happened ad-hoc in the workspace (the exact
"no enforced front-to-back contract" failure the genome-tree lane fixed with tools/build_tree.sh).
This module is the importable, testable core of that missing contract; `tools/build_domain_tree.py`
is the operator CLI.

Pipeline (each stage refuses loudly rather than degrading):
  spec → extract → stage (dedup + length-sanity + min-tips) → align+infer (approval-gated CPU) →
  tree_sanity gate (outgroup-aware) → summary TSV (the Mode-B data contract, card 3/3).

Engine motto: deterministic extraction, judgment deferred. This module assigns no score, promotes no
triage tier, and makes no structure/activity/HGT claim. A domain clade is class-level homology
context only. The ks_phylogeny guards are inherited, not re-implemented: STRAIN-INTERNAL ONLY and the
ITERATIVE-MODULE GUARD live in the extractor; the FALSE-RESCUE token set stays in the corroborator.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter  # v9.7.409 export-injection: CSV formula-cell guard
except ImportError:  # module loaded by file path without a parent package (tests do this)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

# v9.7.409 (DEEP_AUDIT2_resource_dos #5): bound the default mafft/iqtree runner with a wall-clock timeout
# (env MAMEY_SUBPROCESS_TIMEOUT_SEC; default 2 h). A caller-supplied `runner` is used verbatim.
_DEFAULT_TREE_TIMEOUT_SEC = 7200


def _tree_timeout_sec() -> float:
    try:
        val = float(os.environ.get("MAMEY_SUBPROCESS_TIMEOUT_SEC", str(_DEFAULT_TREE_TIMEOUT_SEC)))
        return val if val > 0 else _DEFAULT_TREE_TIMEOUT_SEC
    except (TypeError, ValueError):
        return _DEFAULT_TREE_TIMEOUT_SEC


def _default_tree_runner(cmd, **kw):
    """subprocess.run with check=True and a wall-clock timeout (unless the caller set one)."""
    kw.setdefault("timeout", _tree_timeout_sec())
    return subprocess.run(cmd, check=True, **kw)

# aSDomain module cores (ks_phylogeny.DEFAULT_CLASSES) build strain-internal trees; tailoring
# families (mamey/data/tailoring_families.json, card 2/3) build reference-anchored trees. The
# builder treats both identically once sequences are staged.
MODULE_CORE_CLASSES = ("PKS_KS", "PKS_AT", "Condensation", "AMP-binding", "PKS_KR", "PKS_DH")

# Length sanity windows (aa) per module-core class: below the floor = a fragment that would sit on a
# meaningless long/short branch — EXCLUDED with a receipt; above the ceiling = suspicious fusion or
# mis-span — INCLUDED but flagged, so the operator sees it. Windows are deliberately loose (domain
# spans vary); they exist to catch the 40aa "KS" class of artifact, not to police biology.
LENGTH_WINDOWS = {
    "PKS_KS": (250, 700), "PKS_AT": (200, 600), "Condensation": (250, 650),
    "AMP-binding": (300, 750), "PKS_KR": (120, 450), "PKS_DH": (120, 450),
}
DEFAULT_WINDOW = (80, 1200)   # tailoring families / unknown classes: whole-CDS scale
MIN_TIPS = 4                  # below this a "tree" is decoration, not analysis

REQUIRED_SPEC_KEYS = ("domain_class", "gbk_dir", "outdir", "title", "approved_by")


class DomainTreeError(ValueError):
    """Typed refusal: message starts with a stable CODE token for tests/gates."""


def load_spec(path: Path | str) -> dict:
    """Read + validate DOMAIN_TREE_SPEC.json. Refuses on missing keys, empty approved_by, or an
    unknown domain_class (the known set is named in the refusal, mirroring build_tree.sh)."""
    path = Path(path)
    if not path.exists():
        raise DomainTreeError(f"SPEC_MISSING: no spec file at {path}")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DomainTreeError(f"SPEC_INVALID_JSON: {e}") from e
    missing = [k for k in REQUIRED_SPEC_KEYS if not str(spec.get(k, "")).strip()]
    if missing:
        raise DomainTreeError(f"SPEC_INCOMPLETE: missing/empty {missing} "
                              f"(required: {list(REQUIRED_SPEC_KEYS)})")
    cls = spec["domain_class"]
    known = set(MODULE_CORE_CLASSES) | set(_tailoring_family_names())
    if cls not in known:
        raise DomainTreeError(f"SPEC_UNKNOWN_CLASS: {cls!r} — known classes: {sorted(known)}")
    spec.setdefault("min_tips", MIN_TIPS)
    spec.setdefault("outgroup", None)
    # v9.7.413 standing rule (Alex 2026-09-07): a tree with no recognisable outgroup is itself a gate
    # failure. A within-class paralog panel (every KS domain of one strain) legitimately has no
    # outgroup, so the spec must DECLARE which case it is rather than leave the gate to degrade
    # silently. Refused here, at spec load, so the operator learns BEFORE the CPU-heavy inference
    # rather than after it (build_domain_tree has no skip argument and would discard the run).
    spec.setdefault("allow_no_outgroup", False)
    if not str(spec.get("outgroup") or "").strip() and not spec["allow_no_outgroup"]:
        raise DomainTreeError(
            "SPEC_NO_OUTGROUP_UNDECLARED: this spec names no `outgroup`, and a tree with no "
            "recognisable outgroup fails the HARD sanity gate. Either set `outgroup` to a substring "
            "naming the rooting taxon, or set `allow_no_outgroup: true` to declare a tree that has "
            "no outgroup by construction (a within-class paralog panel).")
    return spec


def _tailoring_family_names() -> tuple:
    """Family names from mamey/data/tailoring_families.json (card 2/3); empty if absent so card 1
    stands alone on the module-core classes."""
    reg = Path(__file__).resolve().parent / "data" / "tailoring_families.json"
    if not reg.exists():
        return ()
    try:
        return tuple(json.loads(reg.read_text(encoding="utf-8")).keys())
    except (json.JSONDecodeError, OSError):
        return ()


def stage_domains(domains: list[dict], domain_class: str, outdir: Path | str,
                  min_tips: int = MIN_TIPS) -> dict:
    """Stage extracted domain dicts (ks_phylogeny/tailoring_extract shape: needs `translation`,
    `locus_tag`, `node`, `region`, plus optional `strain`) into a deterministic FASTA + provenance
    TSV. Dedups byte-identical sequences (receipt kept), applies the length window, refuses < min_tips.

    Returns {fasta, provenance, n_staged, n_dedup, n_short_excluded, n_long_flagged}."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    lo, hi = LENGTH_WINDOWS.get(domain_class, DEFAULT_WINDOW)
    seen: dict[str, str] = {}       # seq-sha1 -> first header (dedup receipt)
    rows, fasta_lines = [], []
    n_dedup = n_short = n_long = 0
    for d in sorted(domains, key=lambda x: (x.get("node", ""), x.get("locus_tag", ""),
                                            x.get("domain_id", ""))):
        seq = re.sub(r"\s+", "", d.get("translation", ""))
        if not seq:
            continue
        hdr = "__".join(str(d.get(k, "?")) for k in ("strain", "node", "region", "locus_tag")) \
              + (f"__{d['domain_id']}" if d.get("domain_id") else "")
        sha = hashlib.sha1(seq.encode()).hexdigest()
        status = "OK"
        if len(seq) < lo:
            status, n_short = "SHORT_EXCLUDED", n_short + 1
        elif len(seq) > hi:
            status, n_long = "LONG_FLAGGED", n_long + 1
        if status != "SHORT_EXCLUDED" and sha in seen:
            status, n_dedup = f"DUP_OF:{seen[sha]}", n_dedup + 1
        rows.append({"header": hdr, "domain_class": domain_class, "aa_len": len(seq),
                     "seq_sha1": sha, "status": status,
                     "matched_tag": d.get("matched_tag", ""), "evalue": d.get("evalue", "")})
        if status in ("OK", "LONG_FLAGGED"):
            seen.setdefault(sha, hdr)
            if not status.startswith("DUP_OF"):
                fasta_lines.append(f">{hdr}\n{seq}")
    staged = sum(1 for r in rows if r["status"] in ("OK", "LONG_FLAGGED"))
    prov = outdir / f"{domain_class}_provenance.tsv"
    with prov.open("w", encoding="utf-8", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=list(rows[0].keys()) if rows else
                           ["header", "domain_class", "aa_len", "seq_sha1", "status",
                            "matched_tag", "evalue"], delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    if staged < min_tips:
        raise DomainTreeError(
            f"STAGE_TOO_FEW_TIPS: {staged} staged sequence(s) for {domain_class} "
            f"(min {min_tips}; short-excluded {n_short}, dedup {n_dedup}). A tree this thin is "
            f"decoration, not analysis — provenance kept at {prov.name}.")
    fasta = outdir / f"{domain_class}_staged.fasta"
    fasta.write_text("\n".join(fasta_lines) + "\n", encoding="utf-8")
    return {"fasta": str(fasta), "provenance": str(prov), "n_staged": staged,
            "n_dedup": n_dedup, "n_short_excluded": n_short, "n_long_flagged": n_long}


def build_tree(staged_fasta: Path | str, outdir: Path | str, approved_by: str,
               threads: int = 4, runner: "callable|None" = None) -> str:
    """mafft --auto → IQ-TREE (-m MFP -B 1000, pinned seed). CPU-heavy → refuses without approved_by
    (tree-approval gate parity with build-ref / run_planned_tree). `runner` is injectable for tests.
    Returns the treefile path."""
    if not str(approved_by).strip():
        raise DomainTreeError("APPROVAL_REQUIRED: CPU-heavy inference needs --approved-by <name> "
                              "(standing tree-approval rule).")
    outdir = Path(outdir)
    run = runner or _default_tree_runner
    aln = outdir / (Path(staged_fasta).stem + ".aln.fasta")
    with aln.open("w") as fh:
        run(["mafft", "--auto", "--anysymbol", str(staged_fasta)], stdout=fh)
    pre = str(outdir / (Path(staged_fasta).stem + ".iq"))
    run(["iqtree", "-s", str(aln), "-m", "MFP", "-B", "1000", "-T", str(threads),
         "-seed", "12345", "-redo", "-pre", pre])
    return pre + ".treefile"


def gate_tree(treefile: Path | str, outgroup: str | None = None,
              require_outgroup: bool = True) -> tuple:
    """The HARD pre-render gate: tree_sanity_check.check() (outgroup-aware since v9.7.398).
    Returns (ok, msg); callers MUST refuse to render on ok=False.

    v9.7.413: `require_outgroup=False` carries the spec's `allow_no_outgroup` declaration through to
    the gate, so a paralog panel is exempted BY DECLARATION and every other tree still FAILs with
    NO_OUTGROUP when its marker is missing or truncated."""
    import importlib.util as _ilu
    import sys as _sys
    tools = Path(__file__).resolve().parent.parent / "tools"
    spec = _ilu.spec_from_file_location("_tsc_domain_tree", tools / "tree_sanity_check.py")
    mod = _ilu.module_from_spec(spec)
    _sys.modules.setdefault("_tsc_domain_tree", mod)
    spec.loader.exec_module(mod)
    return mod.check(str(treefile), outgroup=outgroup, require_outgroup=require_outgroup)


SUMMARY_FIELDS = ["domain_class", "strain", "bgc_id", "node", "tip", "clade_id",
                  "clade_support", "nearest_ref", "nearest_ref_family", "patristic_to_ref"]

# The EXACT column contract tools/domain_phylo_rescue.py::load_clades() requires. That reader is the
# tree-based (SH-aLRT/UFBoot) half of the RG-GMCI two-proof rescue channel, but nothing in the engine
# produced its input — it was hand-built from an external IQ-TREE run, which is why the shipped channel
# went effectively unused. Emitting it here wires the real-tree channel end-to-end and lets the
# in-engine 5-mer proxy (mamey/pks_ks_scan.py `_4B`) be audited against an actual ML tree.
CLADE_TABLE_FIELDS = ["domain_id", "bgc_id", "domain_class", "clade_id", "shalrt", "ufboot", "label"]


def write_clade_table(rows: list[dict], outdir: Path | str, domain_class: str) -> str:
    """Write the domain_phylo_rescue clade table. Deterministic; blank-fills missing support values
    (an absent SH-aLRT/UFBoot stays visibly blank — never invented, and the reader's own support
    threshold then simply excludes that clade)."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"{domain_class}_clade_table.tsv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=CLADE_TABLE_FIELDS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda x: (str(x.get("clade_id", "")), str(x.get("domain_id", "")))):
            w.writerow({k: r.get(k, "") for k in CLADE_TABLE_FIELDS})
    return str(p)


def write_summary(rows: list[dict], outdir: Path | str, domain_class: str) -> str:
    """The Mode-B data contract (card 3/3): domain_tree_summary.tsv. Deterministic; blank-fills
    missing fields — a missing measurement stays visibly blank, never invented."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"{domain_class}_domain_tree_summary.tsv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=SUMMARY_FIELDS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x.get("strain", ""), x.get("tip", ""))):
            w.writerow({k: r.get(k, "") for k in SUMMARY_FIELDS})
    return str(p)
