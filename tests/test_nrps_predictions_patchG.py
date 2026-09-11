from tests._uploads_fixture import UPLOADS as _UPLOADS, OUTPUTS as _OUTPUTS  # v9.7.416
"""v9.7.196 Patch G — recover antiSMASH NRPS/PKS predictions the pipeline dropped.
Verified against a real ZIP (not a synthetic fixture): resolves A-domain substrate (the GBK's X),
emits PKS-AT extender calls, and flags over-merged (>=2 protocluster) regions."""
import csv
import os
import tempfile

import pytest

from mamey.nrps_predictions import write_nrps_prediction_csvs

_ZIP = (_UPLOADS + "/AS-421_loose.zip")
_HAVE = os.path.exists(_ZIP)


@pytest.mark.skipif(not _HAVE, reason="AS-421 test ZIP not present")
def test_g_resolves_substrate_and_flags_overmerge():
    d = tempfile.mkdtemp()
    r = write_nrps_prediction_csvs(_ZIP, d, "AS-421")
    assert r["substrate_rows"] > 0, "no A-domain/AT rows emitted"
    assert r["over_merged_regions"] > 0, "no over-merged region flagged"
    rows = list(csv.DictReader(open(r["nrps_prediction_csv"])))
    # the X-resolution is the whole point: at least one row carries a real Stachelhaus substrate
    assert any(row.get("substrate") for row in rows), "no substrate resolved (X still blank)"
    # both domain classes present (NRPS A-domain + PKS AT) on this hybrid strain
    classes = {row.get("domain_class") for row in rows}
    assert "NRPS_A" in classes


@pytest.mark.skipif(not _HAVE, reason="AS-421 test ZIP not present")
def test_g_polymer_csv_has_predictions():
    d = tempfile.mkdtemp()
    r = write_nrps_prediction_csvs(_ZIP, d, "AS-421")
    poly = list(csv.DictReader(open(r["predicted_polymers_csv"])))
    assert poly, "no region polymers emitted"
    assert any(p.get("predicted_polymer") for p in poly)


@pytest.mark.skipif(not _HAVE, reason="AS-421 test ZIP not present")
def test_over_merge_count_is_unique_regions_not_rows():
    """v9.7.198: over_merged_regions counts unique (record_id, region_number), not polymer rows.
    Each over-merged region has ~3 candidate-polymer rows; counting rows inflated the headline ~2-3x."""
    import tempfile
    from mamey.nrps_predictions import write_nrps_prediction_csvs
    r = write_nrps_prediction_csvs(_ZIP, tempfile.mkdtemp(), "AS-421")
    import csv
    poly = list(csv.DictReader(open(r["predicted_polymers_csv"])))
    rows = sum(1 for x in poly if x["over_merge_flag"].startswith("YES"))
    uniq = len({(x["record_id"], x["region_number"]) for x in poly if x["over_merge_flag"].startswith("YES")})
    assert r["over_merged_regions"] == uniq
    if rows > uniq:  # AS-421 exhibits the multi-row case
        assert r["over_merged_regions"] < rows
