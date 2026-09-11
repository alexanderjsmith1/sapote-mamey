#!/usr/bin/env python3
"""extract_module_core_domains.py — deterministic module-core aSDomain extractor (P358-003 Idea A.1).

Emits the reproducible INPUT to a strain-internal KS/module-core domain tree (the substrate Amber's
AS-XXX tree currently has no engine-side generator for). For a directory of antiSMASH region GBKs it
pulls every module-core aSDomain (PKS_KS/PKS_AT/Condensation/AMP-binding/PKS_KR/PKS_DH by default),
reads the domain's own `/translation`, and writes per-class FASTA + a manifest TSV.

Deterministic extraction, judgment deferred — the engine motto. Non-scoring.

TWO GATES (baked in, per the review lane/VGP 2026-08-10 — these are the hazards that must not be discovered later):
  1. ITERATIVE-MODULE GUARD (VGP): KS count != module count != chain length. An iterative PKS/FAS system is
     COMPLETE at low KS count, so this tool NEVER emits a "missing modules" / "fragmented" claim from a count.
     It reports the raw PKS_KS count per BGC as an OBSERVATION with that caveat stamped on the manifest.
  2. STRAIN-INTERNAL ONLY: one strain per run (asserted from the region-GBK filenames). A cross-strain KS tree
     would fuse e.g. AS-XXX Micromonospora KS with AS-XXX KS (contamination) into a fictitious pathway.

Header format (round-trips): >{strain}__{node}__{region}__{locus_tag}__{domain_id}
CLI:
  python -m tools.extract_module_core_domains <region_gbk_dir> --strain AS-XXX --out <dir> \
      [--classes PKS_KS,PKS_AT,Condensation,AMP-binding,PKS_KR,PKS_DH]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_CLASSES = ("PKS_KS", "PKS_AT", "Condensation", "AMP-binding", "PKS_KR", "PKS_DH")
_NODE_RE = re.compile(r"(NODE_\d+)")
_STRAIN_RE = re.compile(r"^((?:[A-Z]{2,4})[-_]\d{1,6})", re.I)
_REGION_RE = re.compile(r"(region\d+)", re.I)
# aSDomain feature block: header line "     aSDomain   <loc>" then indented /qualifiers until the next feature.
_FEATURE_HDR = re.compile(r"^ {5}(\S+)\s")
_QUAL = re.compile(r'^ {21}/([A-Za-z_]+)=(.*)$')


def _strain_from_name(name: str) -> str | None:
    m = _STRAIN_RE.match(name)
    return m.group(1).upper().replace("_", "-") if m else None


def _parse_gbk_asdomains(text: str, node: str, region: str) -> list[dict]:
    """Regex parse of aSDomain feature blocks. Returns one dict per aSDomain with its /translation."""
    domains: list[dict] = []
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        m = _FEATURE_HDR.match(lines[i])
        if not m or m.group(1) != "aSDomain":
            i += 1
            continue
        quals: dict[str, str] = {}
        cur_key = None
        cur_val: list[str] = []
        i += 1
        while i < n and not _FEATURE_HDR.match(lines[i]):
            qm = _QUAL.match(lines[i])
            if qm:
                if cur_key:
                    quals[cur_key] = "".join(cur_val).strip('"')
                cur_key, cur_val = qm.group(1), [qm.group(2)]
            elif cur_key:
                cur_val.append(lines[i].strip())
            i += 1
        if cur_key:
            quals[cur_key] = "".join(cur_val).strip('"')
        domains.append({
            "domain_class": quals.get("aSDomain", ""),
            "locus_tag": quals.get("locus_tag", ""),
            "domain_id": quals.get("domain_id", ""),
            "label": quals.get("label", ""),
            "evalue": quals.get("evalue", ""),
            "translation": re.sub(r"\s+", "", quals.get("translation", "")),
            "node": node,
            "region": region,
        })
    return domains


def extract(gbk_dir: Path, classes: tuple[str, ...]) -> dict:
    gbks = sorted(gbk_dir.glob("*.gbk"))
    if not gbks:
        raise ValueError(f"no .gbk files in {gbk_dir}")
    named = {p.name: _strain_from_name(p.name) for p in gbks}
    # v9.7.374: the STRAIN-INTERNAL ONLY gate previously only compared strains it COULD parse out
    # of a filename -- a file whose name didn't match _STRAIN_RE (any(s) filtered it out) silently
    # bypassed the check entirely rather than being counted as "unverifiable," while its domains
    # were still merged into `all_domains` below. Two GBKs from genuinely different strains, one
    # named normally and one not, passed this gate and had their KS domains fused into a single
    # "strain-internal" set -- the exact AS-XXX-style contamination chimera this gate exists to
    # prevent (docstring: "the hazards that must not be discovered later"). Fail closed instead:
    # every file in the directory must yield a recognized strain before uniqueness is even checked.
    unrecognized = sorted(name for name, s in named.items() if not s)
    if unrecognized:
        raise ValueError(
            f"STRAIN-INTERNAL ONLY: could not determine a strain id from filename(s) {unrecognized} "
            f"in {gbk_dir} -- cannot verify single-strain safety without it (rename to the project's "
            f"<STRAIN>_NODE_x_regionNNN.gbk convention).")
    strains = set(named.values())
    if len(strains) > 1:
        raise ValueError(f"STRAIN-INTERNAL ONLY: multiple strains in {gbk_dir}: {sorted(strains)}")
    all_domains: list[dict] = []
    for p in gbks:
        node = (_NODE_RE.search(p.name) or [None])[0] if _NODE_RE.search(p.name) else "NODE_?"
        node = _NODE_RE.search(p.name).group(1) if _NODE_RE.search(p.name) else "NODE_?"
        region = (_REGION_RE.search(p.name).group(1) if _REGION_RE.search(p.name) else "region001")
        for d in _parse_gbk_asdomains(p.read_text(encoding="utf-8", errors="replace"), node, region):
            if d["domain_class"] in classes and d["translation"]:
                all_domains.append(d)
    ks_per_node = Counter(d["node"] for d in all_domains if d["domain_class"] == "PKS_KS")
    return {
        "strain": next(iter(strains)) if strains else "UNKNOWN",
        "domains": all_domains,
        "class_counts": dict(Counter(d["domain_class"] for d in all_domains)),
        "ks_per_node": dict(ks_per_node),
    }


def write_outputs(result: dict, out_dir: Path, strain: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_class: dict[str, list[dict]] = defaultdict(list)
    for d in result["domains"]:
        by_class[d["domain_class"]].append(d)
    written = {}
    for cls, doms in sorted(by_class.items()):
        fa = out_dir / f"{strain}_{cls}_domains.faa"
        with fa.open("w", encoding="utf-8") as h:
            for d in doms:
                hdr = f"{strain}__{d['node']}__{d['region']}__{d['locus_tag']}__{d['domain_id']}"
                h.write(f">{hdr}\n{d['translation']}\n")
        written[cls] = len(doms)
    manifest = out_dir / "DOMAIN_MANIFEST.tsv"
    fields = ["strain", "node", "region", "locus_tag", "domain_id", "domain_class", "label", "evalue", "aa_len"]
    with manifest.open("w", encoding="utf-8", newline="") as h:
        h.write("\t".join(fields) + "\n")
        for d in result["domains"]:
            row = [strain, d["node"], d["region"], d["locus_tag"], d["domain_id"],
                   d["domain_class"], d["label"], d["evalue"], str(len(d["translation"]))]
            h.write("\t".join(row) + "\n")
    return {
        "schema": "sapote-module-core-domains-v1",
        "strain": strain,
        "fasta_written": written,
        "class_counts": result["class_counts"],
        "ks_per_node": result["ks_per_node"],
        "claim_safety": [
            "ITERATIVE-MODULE GUARD: KS count != module count != chain length; an iterative system is COMPLETE "
            "at low KS count — a low count is NOT evidence of a missing module or a fragmented pathway.",
            "STRAIN-INTERNAL ONLY: domains are from a single strain; never build a cross-strain KS tree.",
            "Deterministic extraction; homology substrate only; no linkage, activity, or novelty claim.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("gbk_dir", type=Path)
    p.add_argument("--strain", default=None, help="override strain id (else inferred from filenames)")
    p.add_argument("--classes", default=",".join(DEFAULT_CLASSES))
    p.add_argument("--out", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    classes = tuple(c.strip() for c in args.classes.split(",") if c.strip())
    result = extract(args.gbk_dir, classes)
    strain = args.strain or result["strain"]
    summary = write_outputs(result, args.out, strain)
    emit(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
