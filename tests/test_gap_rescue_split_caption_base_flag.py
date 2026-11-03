import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gap_rescue_locus_map import count_sentence

def test_split_with_flags_explains_source_of_flags():
    counts = dict(core=1, reference_genes=2, core_proteins=1, clear=1, ambiguous=0, not_found=0, other=0, set_aside=1, split=1)
    text = count_sentence(counts)
    assert "Of these, 1 was set aside" in text
    assert "Partner-check flags refer to the original match, not necessarily to both displayed split pieces" in text
    assert "1 reference gene is split" in text

def test_no_split_or_no_flag_does_not_claim_flag_qualification():
    base = dict(core=1, reference_genes=2, core_proteins=1, clear=1, ambiguous=0, not_found=0, other=0, set_aside=1, split=0)
    assert "flags refer" not in count_sentence(base)
    base.update(set_aside=0, split=1)
    assert "flags refer" not in count_sentence(base)
