"""INT-2: the TIER_MANIFEST stamp= and the doc build-stamp restatements must be under
sync_version coverage — the fields whose absence let v97319b ship with a stale stamp.
"""
import importlib.util, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
SV = os.path.join(HERE, "..", "tools", "sync_version.py")


def _rules():
    spec = importlib.util.spec_from_file_location("sync_version", SV)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.RULES


def test_tier_manifest_stamp_is_covered():
    # a rule must anchor the stamp= token on TIER_MANIFEST.txt (not just version=)
    hits = [r for r in _rules() if r[0] == "TIER_MANIFEST.txt" and "stamp=" in r[1].pattern]
    assert hits, "TIER_MANIFEST.txt stamp= has no sync rule (INT-2 regression)"


def test_doc_build_stamps_are_covered():
    targets = {"TIER_SET_EXPLAINER.md",
               "docs/user_guides/comprehensive_glossary.md",
               "docs/user_guides/sapote_kernel_guide.md",
               "docs/user_guides/operational_reference.md"}
    covered = {r[0] for r in _rules()}
    missing = targets - covered
    assert not missing, f"build-stamp docs uncovered by sync_version (INT-2 regression): {missing}"
