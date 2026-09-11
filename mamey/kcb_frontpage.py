"""
kcb_frontpage — read the antiSMASH "Most similar known cluster" column, for every region.

This is the highest-signal, lowest-cost information in an antiSMASH run: the named
KnownClusterBlast (KCB) hits. It must be read FIRST — before any scanner — so obvious
named chemistry (mycotrienin, selvamicin, ...) is never missed.

CRITICAL: a KCB hit is a LEAD, not a verdict. similarity% alone is misleading —
similarity=100% with 1 matching gene is a single-protein coincidence, while
similarity=50% with 26 matching genes is a real cluster match. This reader always
reports matching-gene count alongside similarity, and a corroboration tier derived
from both. Scanners still run on every region; KCB gives a name to check against.

    hits = read_frontpage("path/to/antismash_output")
    -> [{region, compound, similarity, n_genes, tier, product}], ranked.
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
import re, json, glob
import sys as _sys


def _corroboration_tier(similarity, n_genes):
    """Combine similarity% and matching-gene count into an interpretable tier.
    Neither signal alone suffices: similarity=100%/1-gene is a single-protein coincidence;
    similarity=50%/26-genes is a real cluster relationship. Require BOTH."""
    sim = similarity or 0
    g = n_genes or 0
    if sim >= 40 and g >= 8:
        return "STRONG"          # high similarity AND many genes = real cluster match
    if sim >= 25 and g >= 5:
        return "MODERATE"        # substantial on both axes
    if sim >= 80 and g <= 2:
        return "COINCIDENTAL"    # high % but 1-2 genes — single-protein fluke, NOT a cluster
    if sim >= 15 and g >= 4:
        return "WEAK"            # a distant relative
    if g >= 8 and sim < 15:
        return "LARGE_GENERIC"   # big region shares generic genes with many MIBiG clusters
    return "LOW"


def read_frontpage(strain_dir):
    jsf = [f for f in glob.glob(f"{strain_dir}/**/regions.js", recursive=True)
           if "MACOSX" not in f]
    if not jsf:
        return []
    txt = open(jsf[0], encoding="utf-8", errors="ignore").read()
    m = re.search(r'var\s+resultsData\s*=\s*(\{.*\});?\s*$', txt, re.DOTALL)
    if not m:
        return []
    try:
        rd = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    def find_kcb(d):
        hits = []
        if isinstance(d, dict):
            if d.get("variant_name") == "knownclusterblast":
                for mt in d.get("matches", []):
                    hits.append({
                        "compound": mt.get("label", "").split(": ")[-1],
                        "similarity": mt.get("similarity"),
                        "n_genes": len(mt.get("genes", [])),
                        "product": mt.get("product"),
                        "accession": mt.get("accession"),
                    })
            for v in d.values():
                hits += find_kcb(v)
        elif isinstance(d, list):
            for v in d:
                hits += find_kcb(v)
        return hits

    out = []
    for anchor, detail in rd.items():
        hits = find_kcb(detail)
        if hits:
            top = hits[0]              # antiSMASH's own top-ranked hit (= front-page display)
            top["tier"] = _corroboration_tier(top["similarity"], top["n_genes"])
            top["region"] = anchor
            top["alt_hits"] = [h["compound"] for h in hits[1:4]]
            out.append(top)
    # rank: STRONG first, then by gene count
    order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "LARGE_GENERIC": 3, "COINCIDENTAL": 4, "LOW": 5}
    out.sort(key=lambda h: (order.get(h["tier"], 6), -(h["similarity"] or 0)))
    return out


def frontpage_command(args):
    hits = read_frontpage(args.strain_dir)
    if not hits:
        emit("No KnownClusterBlast hits found (is this an antiSMASH output dir with regions.js?)")
        return 1
    # v9.7.230 (audit #5): region/node/bgc filtering for card authoring — the reader returned every
    # region, forcing manual grep. --region matches the region label (e.g. r32c1 or region001); --node
    # and --bgc match when the hit carries those keys.
    # v9.7.243 (H-003, owned retraction). `read_frontpage` sets only `region`. Verified against a real
    # 14 MB antiSMASH regions.js: the anchors are `r1c1`-style and the per-region detail carries NO
    # contig, seq_id, or Mamey BGC id — so the `--node` / `--bgc` filters I added in .230 matched an
    # always-absent key and returned "no hits after filter" on every real run. They passed CI only
    # because my test stubbed `bgc_id` into the hit dicts: a proxy, not the artifact.
    # A BGC->anchor map needs antiSMASH's record index, which regions.js does not expose. Rather than
    # fake it, the flags are removed; `--region` (the anchor filter) is the supported surface, and
    # `<strain>_2b_bgc_crosswalk.csv` is where BGC -> NODE·region lives.
    _reg = getattr(args, "region", None)
    for _dead in ("node", "bgc"):
        if getattr(args, _dead, None):
            emit(f"kcb-frontpage: --{_dead} is not supported — antiSMASH regions.js carries no contig "
                  f"or BGC id, only region anchors (r1c1...). Filter with --region, or map the BGC to "
                  f"its NODE·region with `<strain>_2b_bgc_crosswalk.csv` first.", file=_sys.stderr)
            return 2
    if _reg:
        hits = [h for h in hits if _reg.lower() in str(h.get("region", "")).lower()]
    if not hits:
        emit(f"No KnownClusterBlast hits after filter (region={_reg}).")
        return 1
    emit(f"{'region':9} {'compound':32} {'sim%':>5} {'genes':>6}  tier", "-" * 68, sep="\n")
    for h in hits[: args.top]:
        emit(f"{h['region']:9} {h['compound'][:32]:32} {h['similarity'] or 0:>5} "
              f"{h['n_genes'] or 0:>6}  {h['tier']}")
    return 0
