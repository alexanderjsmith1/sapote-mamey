"""v9.7.86 P-9: bldA/TTA reports NOT_APPLICABLE on non-actinomycetes.

The prior guard (`not is_streptomyces and not tta_per_bgc`) was unreachable: any GC-poor
non-actinomycete always has TTA-bearing BGCs, so the NOT_APPLICABLE branch never fired
and Firmicutes/fungi got false T4 reports. The fix keys NOT_APPLICABLE on the organism's
actino-status, not on TTA presence.
"""
from __future__ import annotations
import pytest

from mamey.cohort_resolver import actino_status


@pytest.mark.parametrize("organism,expected", [
    ("Knufia", "non_actinomycete"),
    ("Melissococcus plutonius", "non_actinomycete"),
    ("Leucocoprinus gongylophorus", "non_actinomycete"),
    ("Aspergillus niger", "non_actinomycete"),
    ("Wolbachia", "non_actinomycete"),
    ("Amycolatopsis", "actinomycete"),
    ("Streptomyces", "actinomycete"),
    ("Saccharopolyspora erythraea", "actinomycete"),
])
def test_actino_status_classifies_cross_kingdom_genera(organism, expected):
    assert actino_status(organism) == expected


def test_blda_branch_logic_keys_on_actino_status():
    # mirror the decision in external_adapters: NOT_APPLICABLE iff non-actinomycete,
    # regardless of TTA presence (the bug was making it depend on tta_per_bgc emptiness)
    from mamey.cohort_resolver import actino_status

    def blda_applies(taxonomy):
        is_strep = any(k in taxonomy.lower() for k in
                       ("streptomyces", "saccharopolyspora", "streptosporangium",
                        "micromonospora", "streptoverticillium"))
        st = actino_status(taxonomy)
        return is_strep or st in ("actinomycete", "unknown")

    # a non-actinomycete with abundant TTA codons must still be NOT_APPLICABLE
    assert blda_applies("Knufia") is False
    assert blda_applies("Melissococcus plutonius") is False
    # actinomycetes apply
    assert blda_applies("Amycolatopsis") is True
    assert blda_applies("Streptomyces coelicolor") is True
