"""Card 10: the locus-comparison adapter passes contig ends and missing stop codons to the renderer."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT))
import gap_directed_rescue as gdr  # noqa: E402
import rescue_locus_comparison as rlc  # noqa: E402


def test_stop_codon_check():
    assert not gdr.lacks_stop("TAA") and not gdr.lacks_stop("tag") and not gdr.lacks_stop("TGA")
    assert gdr.lacks_stop("GCC") and gdr.lacks_stop("")


def _track(lo, hi):
    return {"genes": [{"start": lo, "end": lo + 900}, {"start": hi - 900, "end": hi}]}


def test_contig_ends_passed_only_when_both_lie_near_the_drawn_genes():
    near = rlc.CONTIG_END_NEAR_BP
    assert rlc.with_contig_ends(_track(1000, 12000), 13000)["sequence_length"] == 13000
    assert "sequence_length" not in rlc.with_contig_ends(_track(1000, 12000), 12000 + near + 1)   # far end
    assert "sequence_length" not in rlc.with_contig_ends(_track(near + 1, 12000), 12500)          # far start
    assert "sequence_length" not in rlc.with_contig_ends(_track(1000, 12000), 0)                  # unknown length
