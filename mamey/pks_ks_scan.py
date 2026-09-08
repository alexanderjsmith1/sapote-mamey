"""pks_ks_scan.py — in-engine PKS ketosynthase (KS) intrinsic clade channel.

An automated, deterministic, offline fragment-rescue channel that runs as part of a Mamey run and emits
`{strain}_4B_pks_ks_fragment_scan.csv` beside the RG-GMCI `_4A` artifact. Cross-contig KS clade co-membership is
a REFERENCE-FREE second signal, complementary to RG-GMCI's reference-tiling linkage.

Method (stdlib only — no muscle/iqtree/network, so it is safe in the core run): pull every `PKS_KS` aSDomain
translation from the region GBKs, compute an alignment-free identity proxy (5-mer containment), single-linkage
cluster at a threshold, and report clades that span more than one contig. Deterministic; runtime seconds/strain.

Prototype logic validated by a contributor lane (BLIZZARD_BLUE_15_ks_clade_channel), cross-validated against Amber's
IQ-TREE KS trees (agreement on AS-XXX/677/760 positive + AS-XXX negative control). This module packages that
logic for the engine and adds the `_4B` CSV writer + a summary dict shaped like run_rggmci's return.

CLAIM CEILING (must survive into every output): a shared KS clade is a CANDIDATE LINK, never a rescue and never a
merge. KS phylogeny groups by substrate/clade as well as by pathway (esp. trans-AT); duplicated pathways cluster
too. The channel emits `KS_CLADE_LINK` candidates only; promotion requires the RG-GMCI two-proof gate. Homology-
guided linkage, not nucleotide joining. Judgment deferred.
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
import os
import re
import zipfile
from collections import defaultdict
from .ziputil import regular_file_names

K = 5
MIN_KS_AA = 100                    # a KS domain is ~400 aa; a shorter slice is an unusable stub
DEFAULT_THRESHOLD = 0.40           # top of the stable plateau (BB sweep); a proposal, not a constant
NEAR_IDENTICAL = 0.75              # containment >=0.75 across contigs -> iterative / same-gene split flag

# .366 (AMBER_366_C12, Amber sign-off 2026-08-12): partition the single-linkage pass by antiSMASH KS
# /domain_subtypes so a trans-AT KS cannot join a cis-AT clade by transitivity (kills the substrate-clade
# false positive Amber's trees exposed). Two KS may union ONLY when they carry the SAME named subtype;
# Hybrid-KS joins only Hybrid-KS; unclassified stands as its own group. This changes the _4B CSV (a new
# `ks_subtype` column + subtype-partitioned clades) which is in packaging.py::DETERMINISM_WHITELIST, so it
# re-scores the fingerprint -> engine bump to 1.9.121. The version below self-declares the partition rule.
KS_SUBTYPE_PARTITION_VERSION = "1"
_UNCLASSIFIED_SUBTYPE = "UNCLASSIFIED"


def _norm_subtype(raw: str) -> str:
    """Normalize an antiSMASH /domain_subtypes value to a stable partition key.

    Empty / missing -> UNCLASSIFIED (own group, never unions with anything). Whitespace-collapsed and
    kept verbatim otherwise so an exact-string match partitions Trans-AT-KS / Iterative-KS / Modular-KS /
    Hybrid-KS / Enediyne-KS (and any future subtype) each into their own clade space.
    """
    s = re.sub(r"\s+", " ", (raw or "").strip())
    return s if s else _UNCLASSIFIED_SUBTYPE


def _regions(zf):
    return [n for n in regular_file_names(zf) if re.search(r"\.region\d+\.gbk$", n, re.I)]


def _contig_of(name):
    m = re.search(r"(?:^|/)([^/]+)\.region\d+\.gbk$", name, re.I)
    return m.group(1) if m else name


def _short_contig(contig):
    m = re.search(r"(NODE_\d+)", contig)
    return m.group(1) if m else contig


def ks_domains_from_gbk(text, contig, region):
    """Yield one dict per PKS_KS aSDomain carrying its /translation (>= MIN_KS_AA)."""
    out = []
    blocks = re.split(r"\n     (?=aSDomain  )", text)
    for b in blocks[1:]:
        flat = b.replace("\n                     ", " ")
        dom = re.search(r'/aSDomain="([^"]+)"', flat) or re.search(r'/domain="([^"]+)"', flat)
        if not dom:
            continue
        name = dom.group(1)
        if name not in ("PKS_KS", "ketosynthase") and name != "KS":
            continue
        loc = re.search(r'/locus_tag="([^"]+)"', flat)
        tr = re.search(r'/translation="([^"]+)"', flat)
        if not tr:
            continue
        seq = re.sub(r"\s+", "", tr.group(1))
        if len(seq) < MIN_KS_AA:
            continue
        # .366: carry the antiSMASH KS subtype. The qualifier is /domain_subtypes (PLURAL) on the PKS_KS
        # aSDomain; tolerate the singular spelling too. Absent -> UNCLASSIFIED (own group).
        st = (re.search(r'/domain_subtypes="([^"]+)"', flat)
              or re.search(r'/domain_subtype="([^"]+)"', flat))
        subtype = _norm_subtype(st.group(1) if st else "")
        out.append(dict(contig=contig, short=_short_contig(contig), region=region,
                        locus_tag=loc.group(1) if loc else "?", length=len(seq), seq=seq,
                        subtype=subtype))
    return out


def _kmers(s):
    return {s[i:i + K] for i in range(len(s) - K + 1)}


def _containment(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def run_pks_ks_scan(input_zip, bgcs=None, threshold=DEFAULT_THRESHOLD):
    """Return a summary dict (shaped like run_rggmci) for the KS intrinsic-clade channel.

    Keys: n_ks, n_contigs, threshold, cross_contig_clades (list of dicts), iterative_candidates (int),
    summary_line. `bgcs` is accepted for signature parity / future bgc_id mapping; not required.
    """
    doms = []
    try:
        with zipfile.ZipFile(input_zip) as zf:
            for n in _regions(zf):
                t = zf.read(n).decode("utf-8", "replace")
                r = re.search(r"\.region(\d+)\.gbk$", n, re.I)
                doms += ks_domains_from_gbk(t, _contig_of(n), int(r.group(1)) if r else 0)
    except Exception as e:  # never fail the core run
        return {"n_ks": 0, "n_contigs": 0, "threshold": threshold, "cross_contig_clades": [],
                "iterative_candidates": 0, "error": str(e),
                "summary_line": f"KS-clade channel: skipped ({e})"}

    n = len(doms)
    n_contigs = len({d["short"] for d in doms})
    if n < 2:
        return {"n_ks": n, "n_contigs": n_contigs, "threshold": threshold, "cross_contig_clades": [],
                "iterative_candidates": 0,
                "summary_line": f"KS-clade channel: {n} KS domain(s) — no cross-contig signal possible"}

    for d in doms:
        d["kmers"] = _kmers(d["seq"])
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    max_cross = {}  # (i,j)->containment for cross-contig pairs, to flag near-identical
    for i in range(n):
        for j in range(i + 1, n):
            c = _containment(doms[i]["kmers"], doms[j]["kmers"])
            if doms[i]["short"] != doms[j]["short"]:
                max_cross[(i, j)] = c
            # .366 subtype partition (the phylogenomics lane edge policy): single-linkage union ONLY when both KS carry the
            # SAME NAMED subtype. Hybrid-KS therefore joins only Hybrid-KS; a trans-AT KS can no longer
            # bridge into a cis-AT clade by transitivity. UNCLASSIFIED is deliberately kept OUT of the
            # union-find (so it can never act as a transitivity bridge that merges a blob) — its cross-contig
            # pairs are surfaced PAIRWISE below (the phylogenomics lane ASK-1 ruling (b) + pairwise-not-bridge condition).
            same_named_subtype = (doms[i]["subtype"] == doms[j]["subtype"]
                                  and doms[i]["subtype"] != _UNCLASSIFIED_SUBTYPE)
            if c >= threshold and same_named_subtype:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    clades = defaultdict(list)
    for i in range(n):
        clades[find(i)].append(i)

    cross_clades = []
    iterative = 0
    for cid, members in enumerate(sorted(clades.values(), key=lambda m: -len(m)), 1):
        contigs = sorted({doms[m]["short"] for m in members})
        if len(contigs) < 2:
            continue
        # near-identical cross-contig within this clade?
        cc = [c for (i, j), c in max_cross.items()
              if find(i) == find(members[0]) and find(j) == find(members[0])]
        near = max(cc) if cc else 0.0
        flag = "ITERATIVE/SAME-GENE_SPLIT" if near >= NEAR_IDENTICAL else "KS_CLADE_LINK"
        if flag == "ITERATIVE/SAME-GENE_SPLIT":
            iterative += 1
        # every member shares one subtype (union is subtype-gated), so members[0] names the clade.
        cross_clades.append({
            "clade_id": f"KSC{cid:02d}", "n_ks": len(members), "contigs": contigs,
            "ks_subtype": doms[members[0]]["subtype"],
            "loci": [f"{doms[m]['short']}:{doms[m]['locus_tag']}" for m in members],
            "max_cross_contig_containment": round(near, 3), "flag": flag,
        })

    # .366 UNCLASSIFIED pass (the phylogenomics lane ASK-1 ruling (b) + pairwise-not-bridge): two unsubtyped KS on different
    # contigs whose containment clears the bar are surfaced as an independent PAIRWISE candidate — one
    # 2-member clade per qualifying pair, never single-linkage-merged. An UNCLASSIFIED KS therefore never
    # bridges a blob; each pair stands alone for RG-GMCI's second proof to confirm or kill (two_proof_join).
    unc = [k for k in range(n) if doms[k]["subtype"] == _UNCLASSIFIED_SUBTYPE]
    upair = 0
    for a in range(len(unc)):
        for b in range(a + 1, len(unc)):
            i, j = unc[a], unc[b]
            if doms[i]["short"] == doms[j]["short"]:
                continue
            c = max_cross.get((min(i, j), max(i, j)), 0.0)
            if c < threshold:
                continue
            upair += 1
            uflag = "ITERATIVE/SAME-GENE_SPLIT" if c >= NEAR_IDENTICAL else "KS_CLADE_LINK"
            if uflag == "ITERATIVE/SAME-GENE_SPLIT":
                iterative += 1
            cross_clades.append({
                "clade_id": f"KSU{upair:02d}", "n_ks": 2,
                "contigs": sorted({doms[i]["short"], doms[j]["short"]}),
                "ks_subtype": _UNCLASSIFIED_SUBTYPE,
                "loci": [f"{doms[i]['short']}:{doms[i]['locus_tag']}",
                         f"{doms[j]['short']}:{doms[j]['locus_tag']}"],
                "max_cross_contig_containment": round(c, 3), "flag": uflag,
            })

    sline = (f"KS-clade channel: {n} KS / {n_contigs} contigs; "
             f"{len(cross_clades)} cross-contig clade(s) (KS_CLADE_LINK candidates), "
             f"{iterative} near-identical (iterative/same-gene). CANDIDATES only — gated by RG-GMCI two-proof.")
    return {"n_ks": n, "n_contigs": n_contigs, "threshold": threshold,
            "cross_contig_clades": cross_clades, "iterative_candidates": iterative, "summary_line": sline}


def write_pks_ks_csv(scan, out_path, strain_id=""):
    """Write {strain}_4B_pks_ks_fragment_scan.csv. One row per cross-contig KS clade."""
    _tmp = out_path + ".tmp"
    with open(_tmp, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        w.writerow(["strain", "clade_id", "ks_subtype", "n_ks", "n_contigs", "contigs", "loci",
                    "max_cross_contig_containment", "flag", "ks_subtype_partition_version", "claim_note"])
        note = ("KS_CLADE_LINK candidate: reference-free intrinsic homology; NOT a rescue/merge. "
                "Requires RG-GMCI two-proof to promote. Judgment deferred.")
        for c in scan.get("cross_contig_clades", []):
            w.writerow([strain_id, c["clade_id"], c.get("ks_subtype", _UNCLASSIFIED_SUBTYPE),
                        c["n_ks"], len(c["contigs"]),
                        ";".join(c["contigs"]), ";".join(c["loci"]),
                        c["max_cross_contig_containment"], c["flag"],
                        KS_SUBTYPE_PARTITION_VERSION, note])
    os.replace(_tmp, out_path)
    return out_path


if __name__ == "__main__":  # standalone verification: python -m mamey.pks_ks_scan <zip> [strain]
    import sys, json
    zp = sys.argv[1]
    sid = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(zp).split("_")[0]
    s = run_pks_ks_scan(zp)
    emit(json.dumps({k: v for k, v in s.items() if k != "cross_contig_clades"}, indent=2))
    for c in s["cross_contig_clades"]:
        emit(c["clade_id"], c["flag"], c["contigs"], "max_cc=", c["max_cross_contig_containment"])
