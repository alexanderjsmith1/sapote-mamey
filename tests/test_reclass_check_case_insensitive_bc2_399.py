"""BC2 .399 audit: tools/reclass_check.py compared antiSMASH Products labels against the
curated map's class keys with exact, case-sensitive string matching. The curated map
(tools/reclass_discriminating_domains.json) keys four of its highest-value classes in
UPPERCASE ("NRPS", "T1PKS", "T2PKS", "T3PKS"), but real antiSMASH output for these classes is
LOWERCASE -- confirmed directly against the engine's own production vocabulary in
mamey/class_architecture.py::_REAL_CLASSES ({"nrps", "t1pks", "t2pks", "t3pks", ...}).

Reproduced live against the REAL curated map (not a synthetic one) before fixing: a BGC
labelled the realistic lowercase "t1pks", carrying genuine T1PKS diagnostic domains, was
falsely flagged "undeclared_strong: T1PKS" even though its label already agreed -- because
`if cls in label_toks` never matched "T1PKS" against "t1pks". The inverse gap (check C, "label
lacks its own diagnostic domain") was silently never exercised at all for any lowercase-labelled
BGC of these four classes, since `lt not in classes` was always True.

Matches the project's own documented case-insensitivity-bug-family fix pattern (see
mamey/bgc_citation_gate.py, mamey/validators/node_notation.py, etc.).
"""
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("reclass_check", ROOT / "tools" / "reclass_check.py")
rc = importlib.util.module_from_spec(_s)
_s.loader.exec_module(rc)

REAL_MAP_PATH = ROOT / "tools" / "reclass_discriminating_domains.json"


def _real_map():
    import json
    return json.loads(REAL_MAP_PATH.read_text(encoding="utf-8"))


def _write_pkg(d, products, domains):
    p = Path(d)
    (p / "AS-TEST_4_triage_board.csv").write_text(
        "Rank,BGC_ID,Node_ID,antiSMASH_Region,Products\n"
        f"1,BGC001,NODE_1_length_100000_cov_50,region001,{products}\n"
    )
    (p / "AS-TEST_gene_by_gene_all_bgcs.csv").write_text(
        "bgc_id,locus_tag,sec_met_domains\n"
        f"BGC001,ctg1_1,{domains}\n"
    )
    return str(p)


def test_realistic_lowercase_t1pks_label_not_falsely_flagged_undeclared():
    """The consequential proof: the real curated map, a realistic lowercase antiSMASH label,
    genuine matching domains -- must NOT be flagged (label already agrees)."""
    cmap = _real_map()
    with tempfile.TemporaryDirectory() as d:
        pkg = _write_pkg(d, "t1pks", "PKS_KS;PKS_AT;PKSI-KS_m3")
        out, summary = rc.analyze(pkg, cmap)
        undeclared = [f for e in out for f in e["findings"] if f["kind"] == "undeclared_strong"]
        assert not undeclared, f"lowercase t1pks label with T1PKS domains falsely flagged: {undeclared}"


def test_realistic_lowercase_nrps_label_still_checked_for_missing_domains():
    """The inverse gap: a lowercase 'nrps' label with NO real NRPS-class diagnostic domains
    should still be checkable by (C) -- not silently exempted by the case mismatch."""
    cmap = {
        "classes": {"NRPS": {"discriminating_domains": ["Condensation", "AMP-binding"],
                              "specific_domains": ["Condensation", "AMP-binding"],
                              "min_domains": 2, "require_specific": True}},
        "skip_domain_check": {"classes": []},
    }
    with tempfile.TemporaryDirectory() as d:
        # domains present are unrelated to NRPS -- label_unsupported should fire
        pkg = _write_pkg(d, "nrps", "SomeUnrelatedDomain")
        out, summary = rc.analyze(pkg, cmap)
        unsupported = [f for e in out for f in e["findings"] if f["kind"] == "label_unsupported"]
        assert unsupported, "lowercase 'nrps' label with no support was never checked at all"
        assert unsupported[0]["cls"] == "NRPS"  # reports the map's real casing, not the raw label


def test_existing_uppercase_fixture_behavior_unchanged():
    """No regression: the tool's own existing test fixture (uppercase 'T1PKS' label) must
    still behave identically -- concordant, not flagged."""
    cmap = {
        "classes": {"T1PKS": {"discriminating_domains": ["PKS_KS", "PKS_AT", "PKSI-KS_m3"],
                               "specific_domains": ["PKS_KS", "PKS_AT", "PKSI-KS_m3"],
                               "min_domains": 2, "require_specific": True}},
        "skip_domain_check": {"classes": []},
    }
    with tempfile.TemporaryDirectory() as d:
        pkg = _write_pkg(d, "PKS; T1PKS", "PKS_KS;PKS_AT;PKSI-KS_m3")
        out, summary = rc.analyze(pkg, cmap)
        assert not out, "existing uppercase-concordant fixture must still not flag"
