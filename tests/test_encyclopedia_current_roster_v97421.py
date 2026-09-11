"""Keep claimed current encyclopedia settings bound to their executable owners."""
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def value(filename, name):
    tree = ast.parse((ROOT / 'mamey' / filename).read_text())
    nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    assert len(nodes) == 1
    return ast.literal_eval(nodes[0].value)


def test_current_family_table_matches_dictionary_and_excludes_catalog_names():
    text = (ROOT / 'wiki/Encyclopedia-Volume-IV.md').read_text()
    table = text.split('| Family |', 1)[1].split('**Not CCTT trigger families', 1)[0]
    observed = re.findall(r'^\| \*\*(T43-[A-Z]+)\*\*', table, re.M)
    expected = {key.split('_')[0] for key in value('source_scans.py', 'CCTT_PATTERNS')}
    assert len(observed) == len(set(observed))
    assert set(observed) == expected
    assert not {'T43-TOMM', 'T43-LMPKS', 'T43-SILENT'} & set(observed)


def test_diagnostic_rosters_match_both_executable_sets():
    text = (ROOT / 'wiki/Encyclopedia-Volume-V.md').read_text()
    block = text.split('- **Diagnostic bonus.**', 1)[1].split('- **The Tier-1 floor.**', 1)[0]
    rosters = re.findall(r'\*\*`\{([^}]+)\}`\*\*', block)
    assert len(rosters) == 2
    for observed, name in zip(rosters, ['AF_DIAGNOSTIC_TRIGGERS', 'AB_DIAGNOSTIC_TRIGGERS']):
        assert {part.strip() for part in observed.split(',')} == value('scoring.py', name)


def test_currency_numeric_observations_match_their_owners():
    text = (ROOT / 'wiki/Encyclopedia-Currency.md').read_text()
    rows = re.findall(r'^\| `([^`]+)` \| `([^`]+)` \| `mamey/([^`]+)` \|$', text, re.M)
    assert rows
    for name, observed, filename in rows:
        actual = value(filename, name)
        if isinstance(actual, (set, dict)):
            actual = len(actual)
        assert observed == str(actual), name


def test_every_volume_exposes_its_review_limits():
    volumes = list((ROOT / 'wiki').glob('Encyclopedia-Volume-*.md'))
    assert len(volumes) == 13
    for path in volumes:
        assert '**Currency scope:**' in path.read_text()[:1500], path.name
