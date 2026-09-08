"""v9.7.383 — a JSON-less antiSMASH ZIP must warn, not silently degrade.

bounded/full modes read KCB/RiQ/TIGRFAM from the record JSON. A partial or
web-exported ZIP of only region GBKs carries no JSON, so bounded quietly falls
back to TXT-only KCB with NO TIGRFAM diagnostics — and before this preflight,
did so with no signal at all. These tests pin the warning and its scope:
- bounded on a JSON-less ZIP warns;
- off on the same ZIP does NOT warn (off never opens JSON — absence is expected);
- the _zip_has_record_json detector is correct.
"""
import warnings
import zipfile

import pytest

from mamey import parsers

# A minimal region GBK — enough for the ZIP to look like antiSMASH output. The
# GenBank parse itself is not under test here; the preflight fires before it.
_MINIMAL_REGION_GBK = """LOCUS       NODE_1_length_100_cov_1.region001        100 bp    DNA     linear   UNK 01-JAN-2026
DEFINITION  test region.
FEATURES             Location/Qualifiers
     source          1..100
ORIGIN
        1 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc
       61 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc
//
"""


def _make_zip(tmp_path, with_json):
    z = tmp_path / "AS-TEST.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("NODE_1_length_100_cov_1.region001.gbk", _MINIMAL_REGION_GBK)
        if with_json:
            zf.writestr("AS-TEST.json", '{"records": []}')
    return z


def test_zip_has_record_json_detects_presence(tmp_path):
    assert parsers._zip_has_record_json(_make_zip(tmp_path, with_json=True)) is True
    assert parsers._zip_has_record_json(_make_zip(tmp_path, with_json=False)) is False
    # bad/missing path fails closed to False, never raises
    assert parsers._zip_has_record_json(tmp_path / "does_not_exist.zip") is False


def test_bounded_on_jsonless_zip_warns(tmp_path):
    z = _make_zip(tmp_path, with_json=False)
    with pytest.warns(UserWarning, match="no antiSMASH record JSON"):
        try:
            parsers.parse_bgcs_from_zip(z, json_mode="bounded")
        except Exception:
            # GenBank parsing of the minimal fixture is not what we assert; the
            # preflight warning fires before parsing and is the subject here.
            pass


def test_off_mode_does_not_warn_about_missing_json(tmp_path):
    z = _make_zip(tmp_path, with_json=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            parsers.parse_bgcs_from_zip(z, json_mode="off")
        except Exception:
            pass
    assert not any("no antiSMASH record JSON" in str(w.message) for w in caught), (
        "off mode must not warn about a missing JSON — it never opens one"
    )


def test_bounded_with_json_does_not_warn(tmp_path):
    z = _make_zip(tmp_path, with_json=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            parsers.parse_bgcs_from_zip(z, json_mode="bounded")
        except Exception:
            pass
    assert not any("no antiSMASH record JSON" in str(w.message) for w in caught), (
        "a ZIP that carries the record JSON must not trip the preflight warning"
    )
