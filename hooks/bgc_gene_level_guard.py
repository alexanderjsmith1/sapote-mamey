#!/usr/bin/env python3
"""bgc_gene_level_guard.py — UserPromptSubmit hook.

FORCES gene-level (per-CDS) reading + an RG-GMCI rescue check BEFORE any BGC class/function/"clutter-or-lead"
claim. Encodes a recurring, costly failure mode: classifying (or dismissing) a BGC by its antiSMASH PRODUCT
LABEL alone — e.g. reading `halogenated; saccharide; other` as "weak clutter" — when the CDS-level genes show
a real tailoring module (a tryptophan halogenase + a deoxysugar/glycosylation set) that RG-GMCI links as the
rescued half of a split biosynthetic pathway a stricter antiSMASH run would DROP.

Fires on any prompt that looks like BGC analysis. Injects a HARD checklist as additionalContext. Generic — no
project/organism/strain specifics (the concrete worked example lives in the patch card + memory, not here).
Fast, and always exits 0 (never blocks); silent on any error or on non-BGC prompts.
"""
import json
import re
import sys

# BGC-analysis intent: BGC/region/contig ids, tailoring-class words, rescue/merge/mode-B vocabulary.
_TRIGGER = re.compile(
    r"\b("
    r"BGC[\s_-]?\d+|BGCs?|NODE_\d+|ctg\d+|region\d{2,3}|"
    r"halogen\w*|tailoring|glycosyl\w*|deoxysugar|saccharide|nucleoside|"
    r"over[-\s]?merge|rescue|RG[-_\s]?GMCI|mode[-\s]?b|anti[sS][mM][aA][sS][hH]|"
    r"biosynthetic gene cluster|split[-\s]?pathway|protocluster"
    r")\b",
    re.I,
)

_MSG = (
    "BGC GENE-LEVEL GUARD (read before making ANY claim about a BGC). "
    "Do NOT classify, rank, or dismiss a BGC by its antiSMASH PRODUCT LABEL alone "
    "(e.g. 'halogenated; saccharide; other') — the label hides the genes. Before asserting a BGC's class, "
    "function, novelty, or 'clutter-vs-lead' status you MUST, in order: "
    "(1) READ THE PER-CDS GENES — open the region GBK and read, for each CDS, /gene_functions, sec_met_domain "
    "(+ E-value), aSDomain, smCOG, and /description (or the package's *_2_inventory.csv and *_3_antismash_* "
    "tables). Name the actual genes/domains you see. "
    "(2) CHECK RG-GMCI FOR A RESCUE — look in *_4A_RGGMCI_ranked_pairs.csv (column rggmci_confidence) for a "
    "HIGH_RG_GMCI_RESCUE (or MODERATE candidate) linking an edge/tailoring fragment to a CORE fragment on "
    "another contig. A halogenase or deoxysugar 'saccharide' fragment can be the missing tailoring half of a "
    "real split pathway that a stricter antiSMASH run DROPS — it is NOT automatically clutter. "
    "(3) TREAT edge / loose-only / 'saccharide' / 'halogenated' fragments as CANDIDATES to verify by genes + "
    "RG-GMCI, never as noise to discard by label. "
    "(4) CITE gene-level evidence (CDS, domain, E-value) for every functional claim. Claim-safety: "
    "KCB = similarity not identity; RG-GMCI = homology-guided linkage, not nucleotide joining; judgment deferred."
)


def main():
    try:
        raw = sys.stdin.read()
        prompt = (json.loads(raw).get("prompt", "") if raw.strip() else "")
    except Exception:
        prompt = ""
    if not prompt or not _TRIGGER.search(prompt):
        return 0
    try:
        out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": _MSG}}
        sys.stdout.write(json.dumps(out))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
