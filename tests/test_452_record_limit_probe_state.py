"""The antiSMASH record-limit probe says what it established; an unverified probe is not "no truncation" (P300-125)."""
import zipfile

from mamey.parsers import antismash_record_limit_truncation

_CAP = "WARNING  Only analysing the first 1000 records (increase via --limit)\n"
_CLEAN = "INFO     antiSMASH version: 8.0.4\nINFO     antiSMASH status: SUCCESS\n"


def _zip(tmp_path, members):
    z = tmp_path / "in.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    return z


def test_no_log_is_unavailable_not_a_negative(tmp_path):
    r = antismash_record_limit_truncation(_zip(tmp_path, {"x.region001.gbk": "LOCUS"}))
    assert r["truncated"] is False
    assert r["probe_state"] == "UNAVAILABLE" and r["logs_read"] == 0


def test_unreadable_archive_is_failed(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    r = antismash_record_limit_truncation(bad)
    assert r["truncated"] is False and r["probe_state"] == "FAILED"


def test_unrelated_log_is_not_a_completed_probe(tmp_path):
    r = antismash_record_limit_truncation(_zip(tmp_path, {"pip.log": "Collecting numpy\n"}))
    assert r["truncated"] is False
    assert r["probe_state"] == "UNRECOGNISED_LOG" and r["logs_read"] == 1


def test_clean_antismash_log_is_not_detected(tmp_path):
    r = antismash_record_limit_truncation(_zip(tmp_path, {"run.log": _CLEAN}))
    assert r["truncated"] is False and r["probe_state"] == "NOT_DETECTED"


def test_cap_line_is_observed_and_fields_unchanged(tmp_path):
    r = antismash_record_limit_truncation(_zip(tmp_path, {"run.log": _CLEAN + _CAP}))
    assert r["truncated"] is True and r["analysed"] == 1000
    assert r["probe_state"] == "TRUNCATION_OBSERVED"
    assert r["first_skipped"] is None and r["skipped_count"] == 0
