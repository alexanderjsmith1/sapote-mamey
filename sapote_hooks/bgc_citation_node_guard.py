#!/usr/bin/env python3
"""Guard: refuse a node-less BGC citation in a Mode B report/deliverable.

WAC-01375 fatal-error class: a chat that ignored the front-door rule cited leads by bare strain+BGC
number (no contig node), which merged two distinct AS-XXX loci and mis-attributed an AB prior. This
guard makes the rule un-ignorable at the point a deliverable is written: it scans a target .md for
lines that pair a strain ID with a bare BGC number and no locating token (NODE_/ctgN_N/regionNNN),
and reports them. Wire as a PostToolUse(Write) or Stop hook; exit 2 to block.

Standalone: mirrors mamey/bgc_citation_gate.py so it runs without importing the package.
"""
import json
import re
import sys

_STRAIN = re.compile(r"\b(?:AS|AJS|SID|PENDING)-?\d+\b", re.I)
# Case-insensitive: `bgc016`/`Bgc016` are the same citation as `BGC016` and must not silently
# bypass the guard (mirrors the mamey/bgc_citation_gate.py fix — same root-cause bug).
_BGC = re.compile(r"\bBGC\d+\b", re.I)
_NODE = re.compile(r"NODE_\d+|\bctg\d+_\d+\b|\bregion\d{1,3}\b|\bcontig\b", re.I)
# only police files that look like a Mode B report/review/card deliverable
_TARGET = re.compile(r"(mode.?b|modeb|AF_AB|review|report|leads|shortlist|card)", re.I)


def _nodeless(text):
    return [(i, ln.strip()) for i, ln in enumerate(text.splitlines(), 1)
            if _STRAIN.search(ln) and _BGC.search(ln) and not _NODE.search(ln)]


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    path = (ev.get("tool_input", {}) or {}).get("file_path", "") or ev.get("file_path", "")
    if not path or not path.lower().endswith(".md") or not _TARGET.search(path):
        return 0
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return 0
    hits = _nodeless(text)
    if not hits:
        return 0
    sys.stderr.write(
        "NODE-LESS BGC CITATION (WAC-01375 fatal-error class): "
        f"{len(hits)} line(s) in {path} cite a strain+BGC with no contig node.\n"
        "Cite by node·region (NODE_n_length_L_cov_C / regionNNN), never a bare BGC number — a node-less\n"
        "citation can merge two distinct loci (see the AS-XXX atratumycin/enediyne conflation).\n"
        + "".join(f"  line {ln}: {t[:110]}\n" for ln, t in hits[:8])
    )
    return 2  # block


if __name__ == "__main__":
    sys.exit(main())
