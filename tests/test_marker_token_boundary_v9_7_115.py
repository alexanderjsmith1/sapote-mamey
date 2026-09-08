"""v9.7.115: marker matching must be a bounded token, not a bare substring.

The old patterns in build_genelevel_triage.scan_markers and build_punchcard.collect flagged any
qualifier value CONTAINING the marker token — so 'comp450X' matched p450, 'transMGTase' matched MGT,
and 'StrReductase' matched StrR. The fix requires the marker to sit at a token boundary (letters/
digits bound it; '_' is an allowed separator so Cytochrome_p450_6 / sugar_MGT_1 still match).
"""
import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))


def _write_gbk(cds_qualifiers):
    """cds_qualifiers: list of (locus_tag, qualifier_line). Returns a path to a minimal .gbk."""
    lines = ["LOCUS       TEST", "FEATURES             Location/Qualifiers"]
    for i, (lt, qual) in enumerate(cds_qualifiers, 1):
        lines.append(f"     CDS             {i*100}..{i*100+99}")
        lines.append(f'                     /locus_tag="{lt}"')
        lines.append(f"                     {qual}")
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.gbk")
    open(p, "w").write("\n".join(lines) + "\n")
    return p


def test_triage_rejects_substring_false_positive():
    from build_genelevel_triage import scan_markers
    p = _write_gbk([
        ("ctg1_1", '/gene="comp450X"'),          # FALSE positive under old pattern
        ("ctg1_2", '/sec_met_domain="p450"'),     # true marker
    ])
    found = {(lt, mk) for lt, mk, _ in scan_markers(p)}
    assert ("ctg1_2", "p450") in found
    assert ("ctg1_1", "p450") not in found        # the fix: no substring false positive


def test_triage_accepts_underscore_bounded_token():
    from build_genelevel_triage import scan_markers
    p = _write_gbk([("ctg2_1", '/sec_met_domain="Cytochrome_p450_6"')])
    found = {(lt, mk) for lt, mk, _ in scan_markers(p)}
    assert ("ctg2_1", "p450") in found            # _-bounded token still matches


def test_triage_rejects_MGT_substring():
    from build_genelevel_triage import scan_markers
    p = _write_gbk([
        ("ctg3_1", '/sec_met_domain="transMGTase"'),   # FALSE positive under old pattern
        ("ctg3_2", '/gene="MGT"'),                       # true marker
    ])
    found = {(lt, mk) for lt, mk, _ in scan_markers(p)}
    assert ("ctg3_2", "MGT") in found
    assert ("ctg3_1", "MGT") not in found
