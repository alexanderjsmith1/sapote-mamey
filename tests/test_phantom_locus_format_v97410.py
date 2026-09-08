"""v9.7.410 — PHANTOM_LOCUS must catch a fabricated gene id in ANY format, not only ctgN_M.

The v9.7.246 gate extracted cited loci with a single regex, ``_LOCUS_RE = r"\\bctg\\d+_\\d+\\b"``.
That is the antiSMASH contig-index grammar only. A strain whose deposited genome carries RefSeq-style
locus tags (``KSE_RS#####``), RiPP precursor ids (``allorf_#####_#####``), or ``SCO####`` tags could
have a fabricated member of its OWN id family injected into a card and every guard passed it, even with
``--package`` (the sealed roster available), because the fabricated id was never extracted to be tested.

The generalization: derive the strain's own id-family grammars from the sealed roster
(``bgc_context["known_loci"]``) and flag any card token matching one of those families but absent from
the roster. The ctgN_M path is retained; real roster genes (members, any format) still pass; a foreign
subject accession of a *different* shape is out of scope, so it is not a false positive.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.modeb_structure_gate import (  # noqa: E402
    lint_card,
    readiness_state,
    _READINESS_BLOCKING,
    _phantom_locus_findings,
    _family_skeleton,
)


def _phantom(findings):
    return [f for f in findings if f.get("code") == "PHANTOM_LOCUS"]


# A RefSeq-style roster: this strain's own genes are KSE_RS#####, not ctgN_M.
REFSEQ_ROSTER = {"KSE_RS00100", "KSE_RS00105", "KSE_RS00110", "KSE_RS00115"}


# --- FAIL-BEFORE (v9.7.408): a fabricated RefSeq gene of the strain's own family passes ----------
# On the pristine .408 gate this assertion FAILS (the fabricated KSE_RS99999 produces no
# PHANTOM_LOCUS finding); on the patched gate it PASSES.

def test_fabricated_refseq_gene_of_strain_family_is_caught():
    ctx = {"known_loci": REFSEQ_ROSTER}
    leaked = ("## §4\nPer-gene BLASTp settled the call on gene `KSE_RS99999`, which overturned "
              "the beta-lactamase assignment.\n")
    f = _phantom(lint_card(leaked, bgc_context=ctx))
    assert f, "a fabricated RefSeq-style gene of the strain's own family must raise PHANTOM_LOCUS"
    assert f[0]["severity"] == "ERROR"
    assert "KSE_RS99999" in f[0]["found"]


def test_fabricated_refseq_gene_is_release_blocking():
    assert "PHANTOM_LOCUS" in _READINESS_BLOCKING


# --- Other id formats generalize too ------------------------------------------------------------

def test_fabricated_allorf_precursor_id_is_caught():
    ctx = {"known_loci": {"allorf_013118_013336", "allorf_020001_020222"}}
    leaked = "## §4\nThe RiPP precursor `allorf_999999_999999` carries the core peptide.\n"
    f = _phantom(lint_card(leaked, bgc_context=ctx))
    assert f and f[0]["severity"] == "ERROR"
    assert "allorf_999999_999999" in f[0]["found"]


def test_fabricated_sco_tag_is_caught():
    ctx = {"known_loci": {"SCO6273", "SCO6274", "SCO6275"}}
    leaked = "## §4\nGene SCO9999 encodes the ketosynthase.\n"
    f = _phantom(lint_card(leaked, bgc_context=ctx))
    assert f and "SCO9999" in f[0]["found"]


# --- PASS-AFTER: real roster genes and out-of-family accessions must NOT false-positive ----------

def test_real_refseq_genes_of_this_strain_pass_clean():
    ctx = {"known_loci": REFSEQ_ROSTER}
    card = "## §4\n`KSE_RS00100` and `KSE_RS00110` carry the KS and AT domains.\n"
    assert not _phantom(lint_card(card, bgc_context=ctx))


def test_foreign_subject_accession_of_a_different_shape_is_not_flagged():
    """A §4 BLASTp subject from ANOTHER organism (WP_… RefSeq protein) is a different id family
    than the strain's own KSE_RS##### genes, so it is out of scope — not a phantom."""
    ctx = {"known_loci": REFSEQ_ROSTER}
    card = ("## §4\n`KSE_RS00100` — rank-1 nr hit WP_012345678.1 (polyketide synthase, "
            "*Streptomyces* sp.), 74% id.\n")
    assert not _phantom(lint_card(card, bgc_context=ctx))


def test_mixed_roster_real_ctg_and_refseq_both_pass():
    ctx = {"known_loci": {"ctg10_10", "ctg10_11", "KSE_RS00100"}}
    card = "## §4\nctg10_10, ctg10_11 and `KSE_RS00100` are all real here.\n"
    assert not _phantom(lint_card(card, bgc_context=ctx))


# --- The ctgN_M path (v9.7.246) is retained unchanged -------------------------------------------

def test_ctg_phantom_still_caught_positive_control():
    ctx = {"known_loci": {"ctg1_5", "ctg1_6"}}
    leaked = "## §4\nThe channel that settled BGC006 ctg1_99999 (esterase).\n"
    f = _phantom(lint_card(leaked, bgc_context=ctx))
    assert f and f[0]["severity"] == "ERROR"
    assert "ctg1_99999" in f[0]["found"]


def test_foreign_ctg_caught_even_when_strain_is_refseq():
    """A foreign ctg tag matches no roster family here, but the always-on ctgN_M path still flags it."""
    ctx = {"known_loci": REFSEQ_ROSTER}
    leaked = "## §4\nBGC006 ctg12_71 settled the call.\n"
    f = _phantom(lint_card(leaked, bgc_context=ctx))
    assert f and "ctg12_71" in f[0]["found"]


# --- Contract preserved: silent without a roster ------------------------------------------------

def test_silent_when_roster_unknown():
    leaked = "## §4\nGene KSE_RS99999 settled the call.\n"
    assert not _phantom(lint_card(leaked, bgc_context={}))
    assert not _phantom(lint_card(leaked, bgc_context={"known_loci": set()}))


# --- Skeleton-derivation unit checks (determinism + distinctiveness gate) ------------------------

def test_family_skeleton_shapes():
    assert _family_skeleton("KSE_RS00100") == (r"KSE_RS\d+", True)
    assert _family_skeleton("allorf_013118_013336") == (r"allorf_\d+_\d+", True)
    assert _family_skeleton("SCO6273") == (r"SCO\d+", True)
    # too broad to be a trustworthy family matcher: 1-char alpha prefix, no separator
    _, distinctive = _family_skeleton("A1")
    assert distinctive is False
    # no digit run at all -> not a numbered-id family
    assert _family_skeleton("promoter") == (None, False)


def test_phantom_findings_are_deterministic():
    ctx = {"known_loci": REFSEQ_ROSTER}
    leaked = "## §4\n`KSE_RS99999` and `KSE_RS88888` were both cited.\n"
    a = _phantom_locus_findings(leaked, ctx)
    b = _phantom_locus_findings(leaked, ctx)
    assert a == b
    assert "KSE_RS88888" in a[0]["found"] and "KSE_RS99999" in a[0]["found"]
