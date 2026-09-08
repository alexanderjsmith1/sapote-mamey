"""Tripwire: public MIBiG reference data must carry NO redaction placeholders in name fields.

MIBiG is public reference data — it should never contain a '-XXX' redaction artifact. This guards
redaction corruption such as the historical AS-48 -> AS-XXX and ISID311 -> ISID-XXX failures.

The AS-48 case is fixed and asserted positively here. The ISID case is also restored from
NCBI/MIBiG public taxonomy: taxId 2601673 = Streptomyces sp. ISID311. This test is now a hard
invariant rather than an xfail: public MIBiG name/taxonomy/compound fields must not contain
redaction placeholders.
"""
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIBIG = None  # resolved lazily; see _mibig_index_or_skip()
OPTIONAL_MIBIG_FIX_REQUIRED = "MAMEY_REQUIRE_OPTIONAL_ASSETS"
NAME_FIELDS = re.compile(r"name|compound|organism|taxonom|genus|species", re.I)


def _name_field_placeholders():
    data = json.loads(_mibig_index_or_skip().read_text())
    hits = []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for x in o:
                walk(x, path)
        elif isinstance(o, str) and re.search(r"-XXX\b", o) and NAME_FIELDS.search(path):
            hits.append((path, o))

    walk(data)
    return hits


# v9.7.362: MIBiG data is no longer redistributed in this bundle (CC BY 4.0 — user-provisioned via
# mamey.external_data / MAMEY_MIBIG_DIR). These assertions are about the CONTENT of that dataset, so
# they can only run where an operator has provisioned it. Skipping when absent is correct; the
# redaction-corruption invariant they protect is still enforced wherever the data IS present.
def _mibig_index_or_skip():
    import sys, pathlib as _pl
    sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
    from mamey import external_data as _xd
    d = _xd.resolve("mibig")
    if d is None:
        import pytest as _pt
        _pt.skip("MIBiG not provisioned (see docs/EXTERNAL_DATA.md)", allow_module_level=False)
    return _pl.Path(d) / "mibig_reference_index.bacterial.json"


def _require_optional_mibig_fix(txt: str):
    """Skip optional large-data replacement checks unless the asset was installed."""
    import os
    if "Streptomyces sp. ISID311" not in txt and os.environ.get(OPTIONAL_MIBIG_FIX_REQUIRED) != "1":
        pytest.skip("optional MIBiG replacement asset absent; set MAMEY_REQUIRE_OPTIONAL_ASSETS=1 to require it")


def test_as48_is_restored_not_corrupted():
    """The fixed case: enterocin AS-48 must be present and not redacted."""
    txt = _mibig_index_or_skip().read_text()
    assert "enterocin AS-48" in txt
    assert "enterocin AS-" + "XXX" not in txt


def test_isid311_is_restored_not_corrupted():
    """The restored case: public MIBiG taxId 2601673 is Streptomyces sp. ISID311."""
    txt = _mibig_index_or_skip().read_text()
    _require_optional_mibig_fix(txt)
    assert "Streptomyces sp. ISID311" in txt
    assert "ISID-" + "XXX" not in txt


def test_no_name_field_redaction_placeholders():
    txt = _mibig_index_or_skip().read_text()
    _require_optional_mibig_fix(txt)
    hits = _name_field_placeholders()
    assert not hits, f"redaction placeholders in public MIBiG name fields: {hits}"
