#!/usr/bin/env python3
"""ks_phylogeny.py — in-engine home for the module-core (KS) domain phylogeny channel (C06 / P358-003).

This is the ENGINE placement of the KS-phylogeny rescue channel. It owns two deterministic,
non-scoring functions the pipeline can import (the standalone reader-side CLIs
`tools/extract_module_core_domains.py` and `tools/domain_phylo_rescue.py` remain the operator
entry points; this module is the importable, testable core):

  1. extract_module_core_domains(gbk_dir, classes) — pull every module-core aSDomain
     (PKS_KS / PKS_AT / Condensation / AMP-binding / PKS_KR / PKS_DH) with its own /translation
     from a directory of *single-strain* antiSMASH region GBKs. This is the reproducible INPUT
     to a strain-internal KS tree — the substrate the phylogeny lane's AS-XXX tree had no engine generator for.

  2. route_domain_only_hints(verdicts) — the A.3 wiring. The corroborator
     (tools/domain_phylo_rescue.py::assess) emits two verdicts: CORROBORATED_SPLIT (a two-proof
     rescue: supported clade co-cluster AND RG-GMCI homology) and DOMAIN_ONLY_HINT (supported
     co-cluster but RG-GMCI is silent — advisory, NEVER a rescue). This routes the DOMAIN_ONLY_HINT
     verdicts into an adjudication-queue record so a lane owner (the review lane) can review them, instead
     of them being retained-but-unrouted in the verdict TSV.

Engine motto: deterministic extraction, judgment deferred. This module assigns no score, promotes
no triage tier, and mints no rescue — a DOMAIN_ONLY_HINT stays a hint.

TWO GATES (baked in, per the review lane / an audit lane 2026-08-10 — the hazards that must not be discovered late):
  * ITERATIVE-MODULE GUARD: KS count != module count != chain length. An iterative PKS/FAS system
    is COMPLETE at a low KS count, so a low count is NOT evidence of a missing module or a
    fragmented pathway. This module never emits a "missing/fragmented" claim from a count.
  * STRAIN-INTERNAL ONLY: one strain per extraction (asserted from the region-GBK filenames). A
    cross-strain KS tree would fuse e.g. AS-XXX Micromonospora KS with AS-XXX KS (a contamination
    chimera) into a fictitious pathway.

FALSE-RESCUE GUARD (shared with rggmci.py:289): conserved catalytic domains that converge by
housekeeping chemistry — FAS/fatty-acid KS, FabB/FabF/FabH, hglE-type KS — must never anchor a
rescue. The corroborator excludes them; this module carries the same exclusion token set so the
engine and the reader-side tool agree.
"""
from __future__ import annotations

try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

DEFAULT_CLASSES = ("PKS_KS", "PKS_AT", "Condensation", "AMP-binding", "PKS_KR", "PKS_DH")
DOMAIN_TREE_REQUIRED_TOP_LEVEL = ("strain", "domains", "class_counts", "ks_per_node", "claim_safety")
DOMAIN_TREE_REQUIRED_DOMAIN_FIELDS = (
    "domain_class", "locus_tag", "domain_id", "translation", "node", "region",
)

# Catalytic-domain-class tokens that converge by housekeeping chemistry — never a rescue anchor.
# NOTE these are DOMAIN-CLASS tokens, not BGC-PRODUCT tokens: matching a product token like
# "pks" here would silently drop every PKS_KS domain (the bug caught pre-ship on 2026-08-10).
_EXCLUDED_DOMAIN_TOKENS = frozenset(
    {"fas", "fatty_acid", "fatty-acid", "fabh", "fabf", "fabb", "hgle-ks", "hgle_ks", "hgle"}
)

_NODE_RE = re.compile(r"(NODE_\d+)")
_STRAIN_RE = re.compile(r"^((?:[A-Z]{2,4})[-_]\d{1,6})", re.I)
_REGION_RE = re.compile(r"(region\d+)", re.I)
# aSDomain feature block: header "     aSDomain   <loc>" then indented /qualifiers to next feature.
_FEATURE_HDR = re.compile(r"^ {5}(\S+)\s")
_QUAL = re.compile(r'^ {21}/([A-Za-z_]+)=(.*)$')


def _excluded_domain(domain_class: str, label: str = "") -> bool:
    """True if a domain converges by housekeeping chemistry (FAS/Fab*/hglE). Letter-boundary
    match so 'fas' does not fire inside 'PKS_KS' etc."""
    hay = f"{domain_class} {label}".lower()
    for tok in _EXCLUDED_DOMAIN_TOKENS:
        if re.search(rf"(?<![a-z]){re.escape(tok)}(?![a-z])", hay):
            return True
    return False


def _strain_from_name(name: str) -> str | None:
    m = _STRAIN_RE.match(name)
    return m.group(1).upper().replace("_", "-") if m else None


def _parse_gbk_asdomains(text: str, node: str, region: str) -> list[dict]:
    """Regex parse of aSDomain feature blocks. One dict per aSDomain, with its own /translation."""
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


def extract_module_core_domains(gbk_dir: Path | str,
                                classes: Iterable[str] = DEFAULT_CLASSES) -> dict:
    """Extract module-core aSDomains from a directory of SINGLE-STRAIN region GBKs.

    Returns {strain, domains, class_counts, ks_per_node, claim_safety}. Raises ValueError if the
    directory has no GBKs or mixes strains (STRAIN-INTERNAL ONLY gate).
    """
    gbk_dir = Path(gbk_dir)
    classes = tuple(classes)
    gbks = sorted(gbk_dir.glob("*.gbk"))
    if not gbks:
        raise ValueError(f"no .gbk files in {gbk_dir}")
    named = {p.name: _strain_from_name(p.name) for p in gbks}
    # v9.7.374: the STRAIN-INTERNAL ONLY gate previously only compared strains it COULD parse out
    # of a filename -- a file whose name didn't match _STRAIN_RE (the `if s` filter dropped it)
    # silently bypassed the check entirely rather than being counted as "unverifiable," while its
    # domains were still merged into `all_domains` below. Two GBKs from genuinely different strains,
    # one named normally and one not, passed this gate and had their KS domains fused into a single
    # "strain-internal" set -- the exact AS-XXX-style contamination chimera this gate exists to
    # prevent (docstring: "never build a cross-strain KS tree"). Fail closed instead: every file in
    # the directory must yield a recognized strain before uniqueness is even checked. (Byte-for-byte
    # twin of the fix in tools/extract_module_core_domains.py -- card
    # AUDIT_374_extract_module_core_domains_strain_guard_gap.)
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
        nm = _NODE_RE.search(p.name)
        node = nm.group(1) if nm else "NODE_?"
        rm = _REGION_RE.search(p.name)
        region = rm.group(1) if rm else "region001"
        for d in _parse_gbk_asdomains(p.read_text(encoding="utf-8", errors="replace"), node, region):
            if d["domain_class"] in classes and d["translation"]:
                all_domains.append(d)
    ks_per_node = Counter(d["node"] for d in all_domains if d["domain_class"] == "PKS_KS")
    return {
        "strain": next(iter(strains)) if strains else "UNKNOWN",
        "domains": all_domains,
        "class_counts": dict(Counter(d["domain_class"] for d in all_domains)),
        "ks_per_node": dict(ks_per_node),
        "claim_safety": [
            "ITERATIVE-MODULE GUARD: KS count != module count != chain length; an iterative system "
            "is COMPLETE at a low KS count — a low count is NOT a missing module or a fragmented pathway.",
            "STRAIN-INTERNAL ONLY: domains are from a single strain; never build a cross-strain KS tree.",
            "Deterministic extraction; homology substrate only; no linkage, activity, or novelty claim.",
        ],
    }


def domain_fastas(result: dict) -> dict[str, str]:
    """Render per-class FASTA text from an extract_module_core_domains() result. Non-writing.

    Header round-trips: >{strain}__{node}__{region}__{locus_tag}__{domain_id}
    """
    strain = result.get("strain", "UNKNOWN")
    by_class: dict[str, list[dict]] = defaultdict(list)
    for d in result["domains"]:
        by_class[d["domain_class"]].append(d)
    out: dict[str, str] = {}
    for cls, doms in sorted(by_class.items()):
        lines = []
        for d in doms:
            hdr = f"{strain}__{d['node']}__{d['region']}__{d['locus_tag']}__{d['domain_id']}"
            lines.append(f">{hdr}\n{d['translation']}")
        out[cls] = "\n".join(lines) + ("\n" if lines else "")
    return out


# ── A.3 routing: DOMAIN_ONLY_HINT verdicts → adjudication queue ──────────────────────────────
_QUEUE_FIELDS = [
    "bgc_a", "bgc_b", "queue_reason", "supporting_clades", "domain_classes",
    "n_module_core_domains", "rggmci_homology", "disposition", "note",
]


def route_domain_only_hints(verdicts: list[dict]) -> list[dict]:
    """Filter corroborator verdicts to the DOMAIN_ONLY_HINT set and shape adjudication-queue rows.

    Input: the list of dicts returned by tools/domain_phylo_rescue.py::assess (keys include
    verdict, is_rescue, supporting_clades, domain_classes, n_module_core_domains, rggmci_homology).
    Output: one queue record per DOMAIN_ONLY_HINT pair, with disposition PENDING_ADJUDICATION.
    CORROBORATED_SPLIT verdicts are two-proof rescues and are NOT queued here. This routing assigns
    no score and never converts a hint into a rescue — a lane owner rules on each row.
    """
    queue: list[dict] = []
    for v in verdicts:
        if v.get("verdict") != "DOMAIN_ONLY_HINT" or v.get("is_rescue"):
            continue
        queue.append({
            "bgc_a": v.get("bgc_a", ""),
            "bgc_b": v.get("bgc_b", ""),
            "queue_reason": "SUPPORTED_DOMAIN_COCLUSTER_WITHOUT_RGGMCI",
            "supporting_clades": v.get("supporting_clades", ""),
            "domain_classes": v.get("domain_classes", ""),
            "n_module_core_domains": v.get("n_module_core_domains", 0),
            "rggmci_homology": v.get("rggmci_homology", "ABSENT"),
            "disposition": "PENDING_ADJUDICATION",
            "note": "ADVISORY: module-core domains co-cluster in a supported clade but RG-GMCI does "
                    "not corroborate. A hint for lane-owner review — never a rescue on its own.",
        })
    return queue


def write_adjudication_queue(queue: list[dict], out_path: Path | str) -> dict:
    """Write the routed DOMAIN_ONLY_HINT rows as a TSV for the adjudication queue. Deterministic."""
    import csv
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=_QUEUE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in queue:
            writer.writerow({k: row.get(k, "") for k in _QUEUE_FIELDS})
    return {
        "schema": "sapote-ks-phylogeny-adjudication-queue-v1",
        "queued": len(queue),
        "disposition": "PENDING_ADJUDICATION",
        "non_claims": [
            "Every queued row is a DOMAIN_ONLY_HINT — advisory, never a rescue.",
            "Routing assigns no score and promotes no triage tier; a lane owner adjudicates.",
        ],
    }


# ── Reference-anchored placement: which module of a reference cluster does a query KS sit beside? ──────────
# A strain-internal KS tree cannot say where a fragment of a giant modular PKS belongs. Adding a characterized
# reference cluster's own module KS as labelled tips can: in SID8382 (public WGS WWFZ01), KS domains on ten contigs
# sat one-to-one beside neomediomycin B module KS, in order within each contig, where shared-reference homology could
# not separate the pieces. References are labelled tips, never a second query strain, so the STRAIN-INTERNAL rule
# holds. Placement reads machinery, not product, and module order is not contig order.

REFERENCE_TIP_PREFIX = "MIBiG__"
PLACED = "PLACED_ON_REFERENCE_MODULE"
AMBIGUOUS = "AMBIGUOUS_MODULES"
FAMILY = "MODULE_FAMILY"
UNPLACED = "UNPLACED"
MAX_QUERIES_PER_PLACED_MODULE = 2   # a duplicated module or an overlap; more reads as a family of similar modules
PLACEMENT_FIELDS = ["query", "verdict", "reference", "module", "reference_tips_in_split", "query_tips_in_split",
                    "support_ufboot", "split_size"]


def reference_module_ks(gbk_path: Path | str, accession: str | None = None) -> list[dict]:
    """KS domains of one reference cluster GenBank file, numbered by position along the record.

    Returns [{tip, reference, module, translation}] with tip = MIBiG__<accession>_KS<nn>. antiSMASH writes features
    in position order, so file order is module order along the record.
    """
    p = Path(gbk_path)
    acc = accession or p.name.split(".")[0]
    doms = [d for d in _parse_gbk_asdomains(p.read_text(encoding="utf-8", errors="replace"), "", "")
            if d["domain_class"] == "PKS_KS" and d["translation"]]
    return [{"tip": f"{REFERENCE_TIP_PREFIX}{acc}_KS{i:02d}", "reference": acc, "module": i,
             "translation": d["translation"]} for i, d in enumerate(doms, 1)]


def _parse_newick(text: str) -> tuple[list[int], list[str], list[list[int]]]:
    """Minimal Newick reader: returns (parent, label, children) per node; node 0 is the root.

    Handles IQ-TREE output: quoted or bare tip names, internal labels such as '95.3/100', and branch lengths.
    """
    parent, label, children = [-1], [""], [[]]
    cur, i, n = 0, 0, len(text)
    while i < n:
        c = text[i]
        if c == "(":
            parent.append(cur); label.append(""); children.append([]); children[cur].append(len(parent) - 1)
            cur = len(parent) - 1; i += 1
        elif c == ",":
            p = parent[cur]
            parent.append(p); label.append(""); children.append([]); children[p].append(len(parent) - 1)
            cur = len(parent) - 1; i += 1
        elif c == ")":
            cur = parent[cur]; i += 1
        elif c == ";":
            break
        elif c == ":":
            i += 1
            while i < n and text[i] not in ",();":
                i += 1
        else:
            if c == "'":
                j = text.index("'", i + 1)
                label[cur] = text[i + 1:j]; i = j + 1
            else:
                j = i
                while j < n and text[j] not in ",():;":
                    j += 1
                label[cur] = text[i:j].strip(); i = j
    return parent, label, children


def _ufboot(label: str) -> float | None:
    """UFBoot support from an IQ-TREE internal label ('SH-aLRT/UFBoot' or a single number)."""
    parts = label.split("/")
    try:
        return float(parts[-1])
    except ValueError:
        return None


def place_on_reference_modules(newick_text: str, min_ufboot: float = 80.0,
                               reference_prefix: str = REFERENCE_TIP_PREFIX) -> list[dict]:
    """For each query KS tip, the smallest well-supported split of the tree around it that holds reference KS tips.

    Unrooted and root-independent: every internal branch with UFBoot >= min_ufboot splits the tips in two; the side
    holding the query is a candidate. Of the candidates holding at least one reference tip, the smallest decides:
      PLACED_ON_REFERENCE_MODULE  exactly one reference KS, of one reference (module = its number), shared with at
                                  most one other query KS
      MODULE_FAMILY               one reference KS but more query KS than that: a family of similar modules
      AMBIGUOUS_MODULES           more than one reference KS (several modules or references fit)
      UNPLACED                    no supported split holds a reference KS
    Advisory: it assigns no score and changes no RG-GMCI confidence.
    """
    parent, label, children = _parse_newick(newick_text)
    tips = [k for k in range(len(parent)) if not children[k]]
    below: dict[int, frozenset] = {}
    for k in reversed(range(len(parent))):   # children always follow their parent in creation order
        below[k] = frozenset([label[k]]) if not children[k] else frozenset().union(*(below[c] for c in children[k]))
    alltips = frozenset(label[t] for t in tips)
    splits = []
    for k in range(1, len(parent)):
        if children[k]:
            s = _ufboot(label[k])
            if s is not None and s >= min_ufboot:
                splits.append((below[k], s))
    out = []
    for t in sorted(tips, key=lambda t: label[t]):
        q = label[t]
        if q.startswith(reference_prefix):
            continue
        best = None
        for side, s in splits:
            side = side if q in side else alltips - side
            refs = sorted(x for x in side if x.startswith(reference_prefix))
            if refs and (best is None or len(side) < best[0]):
                best = (len(side), refs, s, len(side) - len(refs))
        if best is None:
            out.append({"query": q, "verdict": UNPLACED, "reference": "", "module": "", "reference_tips_in_split": "",
                        "query_tips_in_split": "", "support_ufboot": "", "split_size": ""})
            continue
        size, refs, s, nq = best
        m = re.match(rf"{re.escape(reference_prefix)}(.+)_KS(\d+)$", refs[0]) if len(refs) == 1 else None
        verdict = AMBIGUOUS if not m else PLACED if nq <= MAX_QUERIES_PER_PLACED_MODULE else FAMILY
        out.append({"query": q, "verdict": verdict,
                    "reference": m.group(1) if m else "; ".join(sorted({re.sub(r"_KS\d+$", "", r[len(reference_prefix):])
                                                                     for r in refs})),
                    "module": int(m.group(2)) if m else "", "reference_tips_in_split": "; ".join(refs),
                    "query_tips_in_split": nq, "support_ufboot": s, "split_size": size})
    return out


def write_placement(rows: list[dict], out_path: Path | str) -> dict:
    """Write placement rows as a TSV. Deterministic."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=PLACEMENT_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in PLACEMENT_FIELDS})
    counts = Counter(r["verdict"] for r in rows)
    return {"schema": "sapote-ks-reference-placement-v1", "counts": dict(counts),
            "non_claims": ["Placement reads KS machinery, not product identity.",
                           "Module order read from a tree is not contig order; it joins nothing.",
                           "Advisory: no score, no triage tier, no RG-GMCI confidence change."]}
