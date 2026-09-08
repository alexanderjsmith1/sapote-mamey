#!/usr/bin/env python3
"""domain_phylo_rescue.py — advisory catalytic-domain-phylogeny corroboration for split-pathway rescue.

Reader-side and NON-SCORING. Given (1) a module-core domain-tree clade table and (2) a package's
RG-GMCI ranked-pairs table, this tool decides, for each candidate cross-BGC pair, whether a
catalytic-domain co-clustering signal CORROBORATES an RG-GMCI/ClusterBlast homology rescue — or is
merely an advisory hint that must NOT be treated as a rescue on its own.

Why this exists (AS-XXX, Amber 2026-08-10): a KS-domain tree places KS aSDomains carried on different
antiSMASH fragments into type-coherent, well-supported clades, linking fragments whose whole-gene
ClusterBlast is too diverged for RG-GMCI to tie. That is a real, complementary homology signal.

Why it is GUARDED (rggmci.py:289): a KS tree ALWAYS clusters KS domains — conserved-domain convergence
(hglE-KS / FAS-KS) mimics co-clustering. So domain co-clustering ALONE is never a rescue. This tool
enforces the project's two-proof rule (memory rggmci-two-proof): domain co-clustering may only
CORROBORATE a rescue that RG-GMCI/ClusterBlast homology also supports.

Verdicts (per unordered BGC pair):
  CORROBORATED_SPLIT  — a well-supported clade contains module-core domains from BOTH BGCs, AND RG-GMCI
                        has a HIGH/MODERATE homology row for that pair.  (two proofs)
  DOMAIN_ONLY_HINT    — the supported-clade co-clustering exists but RG-GMCI does NOT corroborate.
                        ADVISORY ONLY — explicitly NOT a rescue.  (one proof)
Homology-only pairs (RG-GMCI has them, no domain signal) are NOT this tool's job and are left untouched.

Exclusions from corroboration (the convergence guard):
  * FAS / fatty_acid domains (the tree outgroup) and
  * DROP-class backbone tokens (rggmci _R1_DROP_ONLY_TOKENS: other/saccharide/napaa/hgle-ks/hgle/pks/pks-like)
  never contribute a corroborating co-cluster.

Claim-safety: class-level hypothesis; homology hint, not physical linkage; judgment deferred.

CLI:
  python -m tools.domain_phylo_rescue --clades <clade_table.tsv> --rggmci <pkg>_4A_RGGMCI_ranked_pairs.csv \
         [--min-shalrt 80] [--min-ufboot 95] --out <verdicts.tsv>
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Convergence-prone DOMAIN classes that cluster in a KS/domain tree without implying a shared pathway:
# the FAS outgroup and hglE-KS glycolipid backbone (rggmci.py:289 records the hglE-KS false-rescue case).
# NOTE: these are matched with letter-boundaries so "pks" can never substring-hit a real "PKS_KS" domain.
# The BGC-PRODUCT drop-class tokens (saccharide/napaa/pks/pks-like — rggmci _R1_DROP_ONLY_TOKENS) are a
# whole-cluster label concern, NOT a catalytic-domain-class concern, so they are deliberately NOT applied here.
_EXCLUDED_DOMAIN_TOKENS = {"fas", "fatty_acid", "fatty-acid", "fabh", "fabf", "fabb", "hgle-ks", "hgle_ks", "hgle"}
# RG-GMCI confidence values that count as a corroborating homology proof.
_HOMOLOGY_OK = {"HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"}


def _norm_bgc(value: str) -> str:
    return (value or "").strip().upper()


def _excluded_domain(domain_class: str, label: str) -> bool:
    """True for convergence-prone domains (FAS/hglE-KS). Letter-boundary match so "pks" never hits "PKS_KS"."""
    blob = f"{domain_class} {label}".lower()
    return any(re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", blob) for t in _EXCLUDED_DOMAIN_TOKENS)


def load_clades(path: Path) -> list[dict]:
    """Clade table: domain_id, bgc_id, domain_class, clade_id, shalrt, ufboot [, label]."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"domain_id", "bgc_id", "domain_class", "clade_id", "shalrt", "ufboot"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"clade table missing columns: {sorted(missing)}")
        rows = []
        for r in reader:
            rows.append({
                "domain_id": (r.get("domain_id") or "").strip(),
                "bgc_id": _norm_bgc(r.get("bgc_id")),
                "domain_class": (r.get("domain_class") or "").strip(),
                "clade_id": (r.get("clade_id") or "").strip(),
                "shalrt": _to_float(r.get("shalrt")),
                "ufboot": _to_float(r.get("ufboot")),
                "label": (r.get("label") or r.get("domain_id") or "").strip(),
            })
        return rows


def _to_float(value) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return -1.0


def load_rggmci_pairs(path: Path) -> set[frozenset]:
    """Return the set of unordered {bgc_i, bgc_j} pairs that carry a HIGH/MODERATE RG-GMCI homology row.

    Column names vary across engine versions; match leniently on *bgc*/*partner* + a confidence column.
    """
    if path is None:
        return set()
    corroborated: set[frozenset] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        q_col = _first_match(fields, (r"query.*bgc", r"^bgc(_a|_i|_1|_id)?$", r"bgc_a", r"left"))
        p_col = _first_match(fields, (r"partner.*bgc", r"bgc(_b|_j|_2)$", r"bgc_b", r"right", r"partner"))
        c_col = _first_match(fields, (r"rggmci_confidence", r"confidence", r"verdict", r"tier"))
        if not (q_col and p_col and c_col):
            raise ValueError(f"RG-GMCI table needs query/partner/confidence columns; saw {fields}")
        for r in reader:
            conf = (r.get(c_col) or "").strip().upper()
            if conf in _HOMOLOGY_OK:
                a, b = _norm_bgc(r.get(q_col)), _norm_bgc(r.get(p_col))
                if a and b and a != b:
                    corroborated.add(frozenset((a, b)))
    return corroborated


def _first_match(fields: list[str], patterns) -> str | None:
    for pat in patterns:
        for f in fields:
            if re.search(pat, f, flags=re.I):
                return f
    return None


def assess(clades: list[dict], rggmci_pairs: set[frozenset],
           min_shalrt: float = 80.0, min_ufboot: float = 95.0) -> list[dict]:
    """Emit advisory per-pair verdicts. Non-scoring: never returns a score or promotes a tier."""
    # Group domains by clade, keeping only well-supported clades and non-excluded domains.
    by_clade: dict[str, list[dict]] = defaultdict(list)
    for d in clades:
        if _excluded_domain(d["domain_class"], d["label"]):
            continue
        if d["shalrt"] >= min_shalrt and d["ufboot"] >= min_ufboot:
            by_clade[d["clade_id"]].append(d)

    # A clade co-clusters a pair when it holds module-core domains from >=2 distinct BGCs.
    pair_support: dict[frozenset, dict] = {}
    for clade_id, members in by_clade.items():
        bgcs = sorted({m["bgc_id"] for m in members if m["bgc_id"]})
        if len(bgcs) < 2:
            continue
        for i in range(len(bgcs)):
            for j in range(i + 1, len(bgcs)):
                pair = frozenset((bgcs[i], bgcs[j]))
                acc = pair_support.setdefault(pair, {"clades": set(), "classes": set(), "n_domains": 0})
                acc["clades"].add(clade_id)
                acc["classes"].update(m["domain_class"] for m in members if m["bgc_id"] in pair)
                acc["n_domains"] += sum(1 for m in members if m["bgc_id"] in pair)

    verdicts = []
    for pair, acc in sorted(pair_support.items(), key=lambda kv: sorted(kv[0])):
        a, b = sorted(pair)
        corroborated = pair in rggmci_pairs
        verdicts.append({
            "bgc_a": a,
            "bgc_b": b,
            "verdict": "CORROBORATED_SPLIT" if corroborated else "DOMAIN_ONLY_HINT",
            "rggmci_homology": "PRESENT" if corroborated else "ABSENT",
            "supporting_clades": ";".join(sorted(acc["clades"])),
            "domain_classes": ";".join(sorted(acc["classes"])),
            "n_module_core_domains": acc["n_domains"],
            "is_rescue": corroborated,  # only the two-proof verdict is ever a rescue
            "note": ("domain co-clustering corroborates an RG-GMCI homology rescue (two proofs)"
                     if corroborated else
                     "ADVISORY: supported domain co-clustering WITHOUT RG-GMCI homology — NOT a rescue"),
        })
    return verdicts


_FIELDS = ["bgc_a", "bgc_b", "verdict", "rggmci_homology", "supporting_clades",
           "domain_classes", "n_module_core_domains", "is_rescue", "note"]


def write_verdicts(verdicts: list[dict], out_path: Path) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for v in verdicts:
            writer.writerow(v)
    n_res = sum(1 for v in verdicts if v["is_rescue"])
    return {
        "schema": "sapote-domain-phylo-rescue-v1",
        "pairs": len(verdicts),
        "corroborated_split": n_res,
        "domain_only_hint": len(verdicts) - n_res,
        "non_claims": [
            "Domain co-clustering is a homology hint, not physical linkage.",
            "DOMAIN_ONLY_HINT is advisory and is never a rescue.",
            "This tool assigns no score and promotes no triage tier.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--clades", type=Path, required=True)
    p.add_argument("--rggmci", type=Path, default=None)
    p.add_argument("--min-shalrt", type=float, default=80.0)
    p.add_argument("--min-ufboot", type=float, default=95.0)
    p.add_argument("--out", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    clades = load_clades(args.clades)
    pairs = load_rggmci_pairs(args.rggmci) if args.rggmci else set()
    verdicts = assess(clades, pairs, args.min_shalrt, args.min_ufboot)
    summary = write_verdicts(verdicts, args.out)
    emit(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
