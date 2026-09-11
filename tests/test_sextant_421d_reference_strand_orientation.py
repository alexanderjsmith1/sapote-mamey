"""v9.7.421 — a reference stored on the minus strand silently blocks the figure.

Measured on sealed v9.7.420 against `16S Database/rrna16s.sqlite`, over the 59,677 records that carry a
sequence: 95 are stored reverse-complemented. Every one of them is in the non-type pool (92
`pdf_candidate`, 3 `attribute_candidate`); none is a RefSeq type record, which is why no type-only panel
has ever exposed this. After the SEXTANT_421b length guard and the panel's own `uncultured = 0`
requirement, 26 of the 95 remain admissible as references.

A reverse-complemented reference aligns to nothing, so RAxML-NG gives it a terminal branch near 1.0
subs/site and `tree_sanity_check` refuses to render. Observed on the moss Frankia-rooted cohort backbone
(422 tips): terminal p90 = 0.0347, and JN566168.1 at 100.0000 tripped both LONG_TERMINAL and
DOMINATING_BRANCH. The gate behaves correctly; the operator is told a tip name and cannot reach the cause.

The stored record is never rewritten. Only the working panel copy is oriented, and the orientation is
recorded per record so the change is auditable in `_meta.tsv` and the panel receipt.

Real-store tests read the workspace 16S sqlite from the SAPOTE_16S_STORE environment variable and skip
when it is unset or the file is absent (SEXTANT_426: no workspace path is hardcoded).
"""
import importlib.util, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "tools", "phylo_16s_panel.py")
SRC = open(PANEL, encoding="utf-8").read()

STORE = os.environ.get("SAPOTE_16S_STORE", "")

# A plus-strand 16S fragment carrying the 515F landmark, and a 3'-region fragment
# carrying the 1390 landmark. Both are synthetic: the flanks are filler, the
# landmarks are the conserved motifs the orientation test keys on.
PLUS_515 = "ACGTACGTAC" + "GTGCCAGCAGCCGCGGTAA" + "TACGTAGGGTGCAAGCGTTGT"
PLUS_1390 = "TTGGGAGGGA" + "GTACACACCGCCCGTCACGTCACGAAAGTTGGTAACAC" + "CCGAAGCCGGTGG"


def _module():
    spec = importlib.util.spec_from_file_location("_sextant_421d_panel", PANEL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reverse_complement_is_correct_and_an_involution():
    m = _module()
    assert m.reverse_complement("ACGT") == "ACGT"
    assert m.reverse_complement("AAAC") == "GTTT"
    for seq in (PLUS_515, PLUS_1390, "ACGTRYSWKMBDHVN"):
        assert m.reverse_complement(m.reverse_complement(seq)) == seq


def test_ambiguity_codes_complement_to_their_partners():
    """R<->Y, K<->M, B<->V, D<->H; S, W and N are self-complementary."""
    m = _module()
    assert m.reverse_complement("RYKMBVDHSWN") == "NWSDHBVKMRY"


def test_a_plus_strand_record_is_left_exactly_as_deposited():
    m = _module()
    for seq in (PLUS_515, PLUS_1390):
        out, orientation = m.orient_sequence(seq)
        assert out == seq
        assert orientation == "as_deposited"


def test_a_minus_strand_record_is_oriented_and_reported():
    m = _module()
    stored = m.reverse_complement(PLUS_515)
    out, orientation = m.orient_sequence(stored)
    assert out == PLUS_515, "the panel copy is not on the plus strand"
    assert orientation == "reverse_complemented", "the flip must be recorded, not silent"


def test_a_record_with_both_landmarks_is_refused_not_guessed():
    """Negative control: two landmarks is a suspect deposit, not an orientation call."""
    m = _module()
    with pytest.raises(ValueError) as exc:
        m.orient_sequence(PLUS_515 + m.reverse_complement(PLUS_1390))
    assert "ORIENTATION_AMBIGUOUS" in str(exc.value)


def test_a_record_with_neither_landmark_is_not_touched():
    """Short fragments and divergent records must not be flipped on no evidence."""
    m = _module()
    seq = "ACGTACGTACGTACGTACGTACGTACGTACGT"
    out, orientation = m.orient_sequence(seq)
    assert out == seq
    assert orientation == "as_deposited"


def test_orientation_is_carried_into_the_panel_metadata():
    assert "'orientation'" in SRC.split("fields=['tip'")[1][:400], \
        "orientation is not exported, so the change would not be auditable"
    assert "ORIENTATION_NORMALISED" in SRC, "a flipped reference must be announced"


def test_the_stored_record_is_not_rewritten():
    """The lane must not contain an UPDATE against the governed store."""
    assert "UPDATE record" not in SRC
    assert "UPDATE " not in SRC.split("def orient_sequence")[1]


@pytest.mark.skipif(not os.path.exists(STORE), reason="workspace store not present (set SAPOTE_16S_STORE)")
def test_against_the_real_store_the_defect_exists_and_the_fix_covers_it():
    import sqlite3
    m = _module()
    con = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT acc_version, seq, source FROM record WHERE seq IS NOT NULL AND seq != ''").fetchall()
    minus = []
    for acc, seq, source in rows:
        try:
            _, orientation = m.orient_sequence(seq)
        except ValueError:
            continue
        if orientation == "reverse_complemented":
            minus.append((acc, source))
    assert minus, "the store no longer contains the records this guard exists for"
    # The defect is confined to the non-type pool SEXTANT_421 opens up.
    assert not [a for a, s in minus if s == "refseq_type"], \
        "a RefSeq type record now reads as minus-strand; re-derive the landmark test"
    # And every one of them is actually repaired by the flip.
    for acc, _ in minus[:40]:
        seq = con.execute("SELECT seq FROM record WHERE acc_version=?", (acc,)).fetchone()[0]
        fixed, orientation = m.orient_sequence(seq)
        assert orientation == "reverse_complemented"
        assert m.orient_sequence(fixed)[1] == "as_deposited", f"{acc} is still not plus-strand"


@pytest.mark.skipif(not os.path.exists(STORE), reason="workspace store not present (set SAPOTE_16S_STORE)")
def test_the_observed_blocking_reference_is_the_one_that_gets_fixed():
    """JN566168.1 is the tip that failed the moss Frankia backbone at 100.0000."""
    import sqlite3
    m = _module()
    con = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    row = con.execute("SELECT seq FROM record WHERE acc_base='JN566168'").fetchone()
    if row is None:
        pytest.skip("JN566168 not in this store")
    fixed, orientation = m.orient_sequence(row[0])
    assert orientation == "reverse_complemented"
    assert "GTGCCAGC" in fixed.upper() or "GTACACACCGCCCGTCA" in fixed.upper()


@pytest.mark.skipif(not os.path.exists(STORE), reason="workspace store not present (set SAPOTE_16S_STORE)")
def test_a_plus_strand_type_strain_is_not_called_ambiguous():
    """Regression: the landmarks must be specific enough not to fire on the plus strand.

    An 8-mer minus-strand anchor (GCTGGCAC, the reverse complement of the 515F prefix) occurs
    naturally on the PLUS strand of ordinary 16S genes. Measured 2026-09-09 across the store, an
    8-mer anchor set called 191 plus-strand records ambiguous -- 58 of them RefSeq type, including
    Bacillus cereus ATCC 14579 (NR_114582.1), where the spurious 'minus' hit sits at position 461,
    45 nt BEFORE the genuine plus landmark at 506. Those panels would have aborted on a healthy
    reference.
    """
    import sqlite3
    m = _module()
    con = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    for acc in ("NR_114582", "NR_115526", "NR_043403", "NR_036880", "NR_043881"):
        row = con.execute("SELECT seq FROM record WHERE acc_base=?", (acc,)).fetchone()
        if row is None:
            continue
        seq, orientation = m.orient_sequence(row[0])   # must not raise
        assert orientation == "as_deposited", f"{acc} is a plus-strand type strain"
        assert seq == row[0]


@pytest.mark.skipif(not os.path.exists(STORE), reason="workspace store not present (set SAPOTE_16S_STORE)")
def test_ambiguity_is_rare_enough_to_be_a_real_signal():
    """A refusal that fires on hundreds of healthy records is a broken guard, not a guard."""
    import sqlite3
    m = _module()
    con = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT seq FROM record WHERE seq IS NOT NULL AND seq != '' AND is_type = 1").fetchall()
    refused = 0
    for (seq,) in rows:
        try:
            m.orient_sequence(seq)
        except ValueError:
            refused += 1
    assert refused <= 5, (
        f"{refused} of {len(rows)} type strains are refused as ORIENTATION_AMBIGUOUS; "
        "the landmarks are not specific enough")
