"""Supplemental locating-token check for ordered locus citations.

Each alias in a multi-locus line needs its own preceding locating span. A single
citation retains compatibility with trailing locating fields. This narrow check
does not verify full strain / node-or-contig / region / alias identity, resolve
source mappings, or establish scientific acceptance.

Why this guard exists: per-strain display aliases are not stable cross-source join keys.
A citation that omits its locating fields can conflate distinct loci or borrow a
neighbouring citation's location. Every individual locus must display the complete
strain / full node-or-contig / region / BGC alias identity. This supplemental token
check helps detect omissions; a passing line does not verify the identity mapping.
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
        if not _STRAIN_RE.search(line):
            continue
        bgcs = list(_BGC_RE.finditer(line))
        if len(bgcs) == 1:
            missing = not _NODE_RE.search(line)
        else:
            # Ordered citations place locating fields before each alias. Separate
            # spans prevent a neighbour's node or region from satisfying this check.
            missing = any(not _NODE_RE.search(line[bgcs[n-1].end() if n else 0:m.start()])
                          for n, m in enumerate(bgcs))
        if missing:
            out.append((i, line.strip()))
    return out


def gate_text(text: str) -> list[str]:
    """Claim-safety-style findings list (empty = clean)."""
    return [
        f"node-less BGC citation (line {ln}): {txt[:120]!r} — cite by node·region "
        f"(NODE_n_length_L_cov_C / regionNNN), never by bare BGC number"
        for ln, txt in find_nodeless_bgc_citations(text)
    ]
