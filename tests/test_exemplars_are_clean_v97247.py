"""v9.7.247 (F1c) — the cards that define the bar must clear the bar.

v9.7.246 added `PHANTOM_LOCUS` (ERROR, release-blocking) and pointed it at authored cards. It was never
pointed at the bundle's own exemplars — and both of them carried `ctg12_71`, a locus belonging to
*Amycolatopsis* sp. NPDC004378. `docs/modules/MODE_B_DEPTH_POLICY.md` instructs authors to mirror the
exemplar for their class, so the fabricated observation sat in the document whose purpose is to be copied.

No test or gate read `docs/reference/modeb_exemplars/*`. The only reference to them anywhere in the tree
was a *comment* in `mamey/mode_b_quality_gate.py`.

**known_loci sourcing.** There is no sealed package per exemplar, so the locus universe is derived from the
card's own declared contig: a card headed `NODE_5_length_320211_cov_36` may cite `ctg5_*` and nothing else.
*Limitation, stated rather than hidden:* this cannot catch a foreign locus that happens to share the contig
index (a `ctg5_*` tag from another strain). It catches the real defect and every cross-contig leak. A
package-backed check would be strictly stronger and is not available here.
"""
import pathlib, re, sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.modeb_structure_gate import lint_card

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXEMPLARS = sorted((ROOT / "docs" / "reference" / "modeb_exemplars").glob("*_exemplar.md"))

# Pre-existing, non-phantom ERRORs, each with a reason. A ratchet: it may shrink, never grow.
KNOWN_ERRORS = {
    # v9.7.264: ripp/siderophore exemplars replaced with public class exemplars (amethystogenes BGC008
    # class-III lanthipeptide; avermitilis BGC042 desferrioxamine), both carrying §24 — so the old
    # ripp §24 MISSING_CONDITIONAL_SECTION whitelist no longer applies and is removed (ratchet).
}


def _ctx(md: str) -> dict:
    # own-contig sourcing, two modes:
    #   (1) SPAdes/AS-strain cards declare a NODE_<n>_ contig -> own = ctg<n>_ (original behaviour).
    #   (2) finished-genome / public type-strain cards cite an accession contig (e.g. BA000030.4,
    #       CP023690.1) and antiSMASH numbers genes per record (ctg1_*, ctg2_*). When no NODE_ is
    #       present, take the MODAL ctg<n>_ prefix among the card's loci as "own". This still catches
    #       a foreign locus copied from another strain when it carries a different ctg-index (the
    #       ctg12_71 defect class); *limitation, stated not hidden:* it cannot catch a foreign locus
    #       that happens to share the modal ctg-index. A package-backed check would be strictly
    #       stronger and is not available here.
    m = re.search(r"NODE_(\d+)_", md)
    if m:
        own_idx = m.group(1)
    else:
        idxs = re.findall(r"\bctg(\d+)_\d+\b", md)
        # (3) v9.7.372: a reference exemplar on a complete public genome (Kitasatospora setae
        #     Full48) cites the annotation's NATIVE locus tags (KSE_*) and an accession contig
        #     (NC_016109.1) — zero ctg-numbered loci, so the cross-ctg leak surface this check
        #     polices does not exist. Require the accession declaration, then report no-ctg mode.
        if not idxs and re.search(r"\b(?:NC_|NZ_|CP|BA|AP)\d+(?:\.\d+)?\b", md):
            # known_loci = the card's own native tags, so PHANTOM_LOCUS still fires on any
            # ctg-numbered stray copied in from a SPAdes-era card (there are none today).
            return {"known_loci": set(re.findall(r"\b[A-Z]{2,4}_(?:RS)?\d{3,}\b", md))}
        assert idxs, "exemplar must declare a NODE contig or cite ctg-numbered loci"
        from collections import Counter
        own_idx = Counter(idxs).most_common(1)[0][0]
    own = f"ctg{own_idx}_"
    return {"known_loci": {l for l in re.findall(r"\bctg\d+_\d+\b", md) if l.startswith(own)}}


def test_there_are_exemplars_to_lint():
    assert EXEMPLARS, "no exemplars found — this gate would pass vacuously"


@pytest.mark.parametrize("path", EXEMPLARS, ids=lambda p: p.name)
def test_exemplar_cites_no_foreign_locus(path):
    md = path.read_text(encoding="utf-8")
    phantom = [f for f in lint_card(md, bgc_context=_ctx(md)) if f["code"] == "PHANTOM_LOCUS"]
    assert not phantom, f"{path.name}: {phantom[0]['found'] if phantom else ''}"


@pytest.mark.parametrize("path", EXEMPLARS, ids=lambda p: p.name)
def test_exemplar_has_no_unexpected_errors(path):
    md = path.read_text(encoding="utf-8")
    errs = {f["code"] for f in lint_card(md, bgc_context=_ctx(md), check_depth=True)
            if f["severity"] == "ERROR"}
    allowed = KNOWN_ERRORS.get(path.name, set())
    assert not (errs - allowed), f"{path.name}: new ERROR(s) {sorted(errs - allowed)}"
    assert not (allowed - errs), (f"{path.name}: KNOWN_ERRORS lists {sorted(allowed - errs)} which no "
                                  f"longer fires — delete the entry (ratchet)")


@pytest.mark.parametrize("path", EXEMPLARS, ids=lambda p: p.name)
def test_exemplar_still_clears_the_depth_floor(path):
    """Deleting the phantom paragraphs must not drop a card below depth. If it does, that is a second
    finding — say so rather than padding it back up."""
    md = path.read_text(encoding="utf-8")
    thin = [f["code"] for f in lint_card(md, bgc_context=_ctx(md), check_depth=True)
            if f["code"] in ("THIN_CARD", "THIN_SECTION")]
    assert not thin, f"{path.name}: {thin}"


def test_no_exemplar_carries_the_known_fabricated_locus():
    for p in EXEMPLARS:
        t = p.read_text(encoding="utf-8")
        assert "ctg12_71" not in t and "two of ten on BGC006" not in t, p.name
