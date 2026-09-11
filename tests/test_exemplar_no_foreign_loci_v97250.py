"""v9.7.250 — the exemplar cards may not cite a locus from another organism.

v9.7.246 fixed the *emitter* (`modeb_template_emitter._section_body`), which had templated a real
per-gene BLASTp result belonging to *Amycolatopsis* sp. NPDC004378 — including `ctg12_71` — into
every card of every strain. It did not sweep `docs/reference/modeb_exemplars/`.

That omission matters, because the v9.7.246 remediation note names the exemplars explicitly as one
of the two things to check when PHANTOM_LOCUS fires:

    "Check for templated boilerplate carried over from a different strain's session,
     and for a copy-paste from an example card."

Measured on the shipped v9.7.246 tree, before this cut:
    ripp_exemplar.md        (BGC036, NODE_5): 65 distinct loci — 64 ctg5_*,  one ctg12_71
    siderophore_exemplar.md (BGC038, NODE_6): 100 distinct loci — 99 ctg6_*, one ctg12_71

An exemplar is read as a model to copy. A foreign locus in an exemplar is a phantom locus with a
propagation mechanism. This test is the same question PHANTOM_LOCUS asks of an authored card, asked
of the cards we ship as examples: does every cited gene belong to the organism this card is about?

The exemplar header carries `node: NODE_<n>_...`; antiSMASH locus tags on that contig are `ctg<n>_*`.
So the check needs no CDS table — the card states its own contig.
"""
from __future__ import annotations
import collections
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXEMPLARS = sorted((ROOT / "docs" / "reference" / "modeb_exemplars").glob("*_exemplar.md"))

_LOCUS = re.compile(r"\bctg(\d+)_\d+\b")
_NODE = re.compile(r"node:\s*NODE_(\d+)")

# The specific foreign locus of the v9.7.246 leak. Pinned by name so a regression is named, not just counted.
LEAKED_LOCUS = "ctg12_71"


def test_exemplars_exist():
    assert EXEMPLARS, "no exemplar cards found — has docs/reference/modeb_exemplars/ moved?"


@pytest.mark.parametrize("path", EXEMPLARS, ids=lambda p: p.name)
def test_exemplar_cites_only_its_own_contig(path):
    """Every ctgN_M in an exemplar must have N == the card's own contig index.

    Own-contig sourcing, two modes (mirrors test_exemplars_are_clean_v97247._ctx):
      (1) AS-strain/SPAdes cards declare `node: NODE_<n>` in the header -> own = n.
      (2) finished-genome / public type-strain cards cite an accession contig (e.g. BA000030.4)
          with no NODE_ header; antiSMASH numbers genes per record (ctg1_*, ctg2_*), so take the
          MODAL ctg<n> index as own. A foreign locus copied from another strain with a different
          ctg-index (the ctg12_71 defect) is still flagged; a foreign locus sharing the modal
          index is not catchable without a package (limitation stated, not hidden).
    """
    text = path.read_text(encoding="utf-8")
    cited = collections.Counter(mm.group(1) for mm in _LOCUS.finditer(text))
    m = _NODE.search(text.splitlines()[0])
    if m:
        own = m.group(1)
    else:
        # v9.7.372 mode (3): a reference exemplar on a complete public genome (Kitasatospora
        # setae Full48) uses the annotation's native locus tags and an accession contig — zero
        # ctg-numbered loci means zero cross-ctg leak surface for this check. Require the
        # accession declaration; with no cited ctg loci there is nothing foreign to flag.
        if not cited and re.search(r"\b(?:NC_|NZ_|CP|BA|AP)\d+(?:\.\d+)?\b", text):
            return
        assert cited, f"{path.name}: no `node: NODE_<n>` header and no ctg-numbered loci to derive own contig"
        own = cited.most_common(1)[0][0]
    foreign = {c: n for c, n in cited.items() if c != own}
    assert not foreign, (
        f"{path.name} (own contig ctg{own}_) cites loci from other contigs: "
        f"{ {f'ctg{c}_*': n for c, n in foreign.items()} }. "
        "A locus from another organism in an example card is a phantom locus with a propagation "
        "mechanism — the card is read as a model to copy. Delete the sentence; do not reword it."
    )


@pytest.mark.parametrize("path", EXEMPLARS, ids=lambda p: p.name)
def test_exemplar_free_of_the_v97246_leak(path):
    """Named regression: the exact locus templated into 74 cards must not reappear."""
    assert LEAKED_LOCUS not in path.read_text(encoding="utf-8"), (
        f"{path.name} carries {LEAKED_LOCUS}, the *Amycolatopsis* sp. NPDC004378 locus that "
        "v9.7.246 removed from the emitter but not from the exemplars."
    )


def test_emitter_body_carries_no_foreign_locus():
    """The emitter's *emitted body* must be clean. Its comments may name the leak (they document it)."""
    src = (ROOT / "mamey" / "modeb_template_emitter.py").read_text(encoding="utf-8")
    body = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert LEAKED_LOCUS not in body, (
        f"{LEAKED_LOCUS} is present in non-comment source of modeb_template_emitter.py"
    )
