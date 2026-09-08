"""Fail-closed node·region citation gate for BGC-level deliverables.

FATAL-ERROR CLASS (WAC-01375 audit, 2026-08-28). A cross-strain Mode B review cited leads by bare
`strain + BGC-number` with no contig node. BGC numbers are per-strain Mamey DISPLAY labels — not stable
join keys, not comparable across strains/sources/engine versions. The shortcut MERGED two physically
distinct AS-XXX loci (atratumycin `NODE_35/BGC016` vs enediyne `NODE_21/BGC011`) and mis-attributed an
AB-94 prior: a labeling omission became a factual error. The Sapote-Mamey standing rule is
"cite BGCs by node·region, never by BGC number".

This gate makes that rule mechanical: any deliverable line that pairs a strain identifier with a bare
`BGC\\d+` and carries NO locating token (NODE_.../ctgN_N/regionNNN/contig) is a node-less citation and is
reported. Fail-closed — a BGC-level deliverable that trips it must be corrected, not shipped.

The check is line-scoped on purpose: a node·region citation is meant to be self-contained where it is
made (`AS-XXX / NODE_35_length_..._cov_... / region001 / BGC016`), so the node must sit with the BGC on
the same line/row. Count phrases ("37 BGCs", "12 BGCs total") never match `BGC\\d+` and so never trip.
"""
import re

# strain identifiers that key a per-strain BGC label
_STRAIN_RE = re.compile(r"\b(?:AS|AJS|SID|PENDING)-?\d+\b", re.I)
# a specific BGC label (BGC012) — NOT the bare word "BGCs". Case-insensitive: `bgc016`/`Bgc016`
# are the same citation as `BGC016` and must not silently bypass the gate.
_BGC_RE = re.compile(r"\bBGC\d+\b", re.I)
# any token that ties the label back to the assembly.
# v9.7.401 (BC2): the last alternative was a bare `\bcontig\b` -- matched the generic NOUN
# "contig" with no accompanying number, so a decoy sentence that merely mentions the word
# ("BGC016 is on a contig, exact node still needs to be checked") satisfied this check and the
# line was never reported. That is the exact WAC-01375 defect class this gate exists to catch --
# a strain+BGC citation with no actual locating value -- wearing a disguise. Reproduced live
# against the real pristine function: the decoy sentence above returned zero findings. Checked
# the full shipped corpus (every tracked .md file) for lines that currently rely on the BARE
# contig-word alternative to stay unflagged: zero found, so tightening this introduces no known
# regression against real content. Requires "contig" to be paired with a number (contig12,
# contig_12, contig-12, contig 12) to count as an actual locating token, matching how ctg\d+_\d+
# and region\d{1,3} already require a number, not just the bare noun.
_NODE_RE = re.compile(r"NODE_\d+|\bctg\d+_\d+\b|\bregion\d{1,3}\b|\bcontig[\s_-]?\d+\b", re.I)


def find_nodeless_bgc_citations(text: str) -> list[tuple[int, str]]:
    """Return [(line_no, line)] for every line that cites a strain+BGC with no node/region/contig."""
    out: list[tuple[int, str]] = []
    for i, line in enumerate((text or "").splitlines(), 1):
        if _STRAIN_RE.search(line) and _BGC_RE.search(line) and not _NODE_RE.search(line):
            out.append((i, line.strip()))
    return out


def gate_text(text: str) -> list[str]:
    """Claim-safety-style findings list (empty = clean)."""
    return [
        f"node-less BGC citation (line {ln}): {txt[:120]!r} — cite by node·region "
        f"(NODE_n_length_L_cov_C / regionNNN), never by bare BGC number"
        for ln, txt in find_nodeless_bgc_citations(text)
    ]
