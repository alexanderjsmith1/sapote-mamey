"""A plant is not an ant.

`tools/bigscape_figure_labels.category_of` ended with a bare substring test over
`_HABITAT_ALIASES`, which contains `"ant" -> attine` and `"bee" -> bee/wasp`. Those are substrings
of very ordinary words in an actinomycete corpus. Measured on the shipped rule: "plant root",
"rhizosphere of a plant", "Antarctic soil", "Atlantic sediment", "plantation soil", "elephant dung"
and "giant panda faeces" all returned ATTINE; "beech forest soil" returned BEE/WASP; and the real
host "Apis mellifera" returned UNASSIGNED. The rule was close to anti-correlated with the truth on
those inputs.

Isolation source is reported as deposited and never inferred, so `unassigned` is the correct answer
whenever the deposited string does not actually name a known habitat.

Both directions are pinned here. The second class is the one that makes this patch safe to land: a
census of the 176-row consolidated metadata table and the 71-row reference registry found that
every fallthrough assignment in the live corpus was CORRECT, so the fix has to stop the false
positives without changing any of them.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bigscape_figure_labels import category_of  # noqa: E402


# Ordinary deposited isolation sources that the substring rule captured. None of these names an
# ant, a bee or a wasp.
@pytest.mark.parametrize("source", [
    "plant root",
    "rhizosphere of a plant",
    "plantation soil",
    "Antarctic soil",
    "Atlantic sediment",
    "elephant dung",
    "giant panda faeces",
    "beech forest soil",
    "beetle gut",
    "marine sponge",
    "deciduous plant litter",
    "mangrove sediment",
])
def test_an_ordinary_source_is_not_given_a_host(source):
    assert category_of(source) == "unassigned", (
        f"{source!r} was assigned a host category it does not name")


# The strings that actually appear in the corpus. These must keep the categories they have, or the
# patch would silently relabel real strains while fixing a latent bug.
@pytest.mark.parametrize("source,expected", [
    ("ant-associated (unknown)", "attine"),
    ("ant-associated (attine fungus-growing ant)", "attine"),
    ("atta (attine ant)", "attine"),
    ("acromyrmex (attine ant)", "attine"),
    ("fungal ant-cultivar (not actinomycete)", "attine"),
    ("moss-associated (ontario)", "bryophyte"),
    ("moss-associated (new jersey)", "bryophyte"),
    ("liverwort-associated (new jersey)", "bryophyte"),
    ("bee or wasp (hymenoptera confirmed; which unresolved)", "bee/wasp"),
])
def test_the_live_corpus_strings_are_unchanged(source, expected):
    assert category_of(source) == expected


@pytest.mark.parametrize("source,expected", [
    ("bee", "bee/wasp"),
    ("wasp", "bee/wasp"),
    ("moss", "bryophyte"),
    ("lichen", "lichen"),
    ("termite", "termite"),
    ("clinical", "clinical"),
])
def test_exact_aliases_still_resolve(source, expected):
    assert category_of(source) == expected


def test_a_hyphen_is_a_token_boundary_but_a_letter_is_not():
    """`ant-associated` matches because the token ends at the hyphen. `plantation` does not,
    because `ant` there is surrounded by letters."""
    assert category_of("ant-associated soil") == "attine"
    assert category_of("plantation soil") == "unassigned"
    assert category_of("ant") == "attine"
    assert category_of("anther") == "unassigned"


def test_unrecognised_is_unassigned_not_guessed():
    """Unknown sources remain unassigned; producer-recognized hosts have parity tests."""
    for s in ["gut of an unidentified insect", "freshwater lake sediment", "hot spring",
              "an unidentified invertebrate"]:
        assert category_of(s) == "unassigned"
