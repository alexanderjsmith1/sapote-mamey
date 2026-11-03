"""The wiki sidebar's version stamp is owned by tools/sync_version.py, so a cut re-stamps it with the rest."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import sync_version  # noqa: E402


def _sidebar_rules():
    return [r for r in sync_version.RULES if r[0] == "wiki/_Sidebar.md"]


def test_sidebar_has_exactly_one_rule_matching_one_line():
    rules = _sidebar_rules()
    assert len(rules) == 1
    _, pattern, replacement = rules[0]
    text = (ROOT / "wiki" / "_Sidebar.md").read_text(encoding="utf-8")
    assert len(pattern.findall(text)) == 1
    assert replacement == f"*bundle v{sync_version.BUNDLE} \u00b7 engine {sync_version.ENGINE}*"


def test_rule_restamps_an_old_sidebar_line():
    _, pattern, replacement = _sidebar_rules()[0]
    old = "**[Sapote\u2013Mamey](Home.md)**\n\n*bundle v9.7.1 \u00b7 engine 1.0.0*\n\n**Start**\n"
    new, n = pattern.subn(replacement, old)
    assert n == 1 and replacement in new and "v9.7.1 " not in new


def test_a_historical_mention_elsewhere_in_the_sidebar_is_not_touched():
    _, pattern, _ = _sidebar_rules()[0]
    assert not pattern.search("See the v9.7.401 notes \u00b7 engine 1.9.100 for history.")
