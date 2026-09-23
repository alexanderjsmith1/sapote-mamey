"""Host vocabulary parity uses the bundled producer table, without a workspace corpus."""
import ast
from pathlib import Path
import pytest
from tools import bigscape_figure_labels as labels


def test_host_vocabulary_matches_producer_in_order():
    source = Path(__file__).resolve().parents[1] / "tools/mamey_habitat_map.py"
    module = ast.parse(source.read_text())
    rules = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "RULES" for t in n.targets))
    mapping = {"bee": "bee/wasp", "wasp": "bee/wasp", "moss": "bryophyte", "termite": "termite", "attine": "attine", "clinical": "clinical"}
    assert labels._HOST_RULES == [(rx, mapping[category]) for rx, category in rules if category in mapping]


@pytest.mark.parametrize("source,category", [("Bombus sp.", "bee/wasp"), ("bumblebee", "bee/wasp"), ("Apis mellifera", "bee/wasp"), ("honeybee (Apis mellifera)", "bee/wasp"), ("Macrotermes natalensis", "termite"), ("Pseudonocardiaceae from Atta", "attine"), ("fungus-growing termite mound", "termite")])
def test_host_names_match_producer(source, category):
    assert labels.category_of(source) == category


@pytest.mark.parametrize("source", ["plantation soil", "Antarctic soil", "beech forest soil", "beetle gut", "elephant dung", "giant panda faeces", "deciduous plant litter"])
def test_host_rule_does_not_reintroduce_substring_false_positives(source):
    assert labels.category_of(source) == "unassigned"


def test_explicit_reference_and_mibig_precedence_is_preserved():
    assert labels.category_of("Bombus sp.", is_mibig=True) == labels.MIBIG
    assert labels.category_of("reference/type") == labels.TYPE_STRAIN
