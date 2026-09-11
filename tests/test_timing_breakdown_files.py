"""test_timing_breakdown_files.py — timing breakdown telemetry tests (v9.7.81).

Acceptance criteria from PATCH_TIMING_BREAKDOWN_INSTRUMENTATION_v9.7.81.md:
  - mamey run --mode smoke --chatgpt-safe writes JSON, CSV, and MD timing files.
  - Sum of phase elapsed seconds <= process elapsed seconds + 1.0s tolerance.
  - A failing phase records status=FAIL before propagating the exception.
  - timing files are present (checksum integrity verified separately in
    test_timing_manifest_pointer.py).
"""
import csv
import json
import time

import pytest

from mamey.timing import TimingRecorder, PhaseTiming


# ---------------------------------------------------------------------------
# Unit: TimingRecorder core contract
# ---------------------------------------------------------------------------

def test_phase_records_elapsed_seconds(tmp_path):
    """A completed phase must have elapsed_seconds set and >= 0."""
    rec = TimingRecorder("TEST", "smoke", "1.9.84")
    with rec.phase("test_phase"):
        time.sleep(0.01)
    assert len(rec.phases) == 1
    p = rec.phases[0]
    assert p.status == "PASS"
    assert p.elapsed_seconds is not None
    assert p.elapsed_seconds >= 0.009  # allow generous lower bound


def test_phase_failure_records_fail(tmp_path):
    """A failing phase must record status=FAIL before re-raising."""
    rec = TimingRecorder("TEST", "smoke", "1.9.84")
    with pytest.raises(ValueError):
        with rec.phase("bad_phase"):
            raise ValueError("deliberate test failure")
    assert rec.phases[0].status == "FAIL"
    assert rec.phases[0].elapsed_seconds is not None


def test_phase_sum_le_process_elapsed(tmp_path):
    """Sum of phase elapsed seconds <= process elapsed + 1.0s tolerance."""
    rec = TimingRecorder("TEST", "smoke", "1.9.84")
    for name in ("alpha", "beta", "gamma"):
        with rec.phase(name):
            time.sleep(0.005)
    data = rec.finish()
    phase_sum = sum(p["elapsed_seconds"] for p in data["phases"]
                    if p["elapsed_seconds"] is not None)
    process_elapsed = data["process"]["elapsed_seconds"]
    assert phase_sum <= process_elapsed + 1.0, (
        f"phase_sum={phase_sum:.3f} > process_elapsed={process_elapsed:.3f} + 1.0s"
    )


def test_write_emits_three_files(tmp_path):
    """write() must produce JSON, CSV, and MD files."""
    rec = TimingRecorder("STRAIN1", "smoke", "1.9.84")
    with rec.phase("antismash_kcb_riq_parse", notes="test phase"):
        time.sleep(0.001)
    rec.write(tmp_path, raw_bgcs=12, corrected_bgcs=8.5)
    assert (tmp_path / "STRAIN1_timing_breakdown.json").exists()
    assert (tmp_path / "STRAIN1_timing_breakdown.csv").exists()
    assert (tmp_path / "STRAIN1_timing_breakdown.md").exists()


def test_json_schema(tmp_path):
    """timing JSON must have required top-level keys and at least one phase."""
    rec = TimingRecorder("STRAIN1", "smoke", "1.9.84",
                         workflow_version="9.7.81", chatgpt_safe=True,
                         input_zip_bytes=1024)
    with rec.phase("antismash_kcb_riq_parse"):
        pass
    data = rec.write(tmp_path, raw_bgcs=5, corrected_bgcs=4.0)
    required = {"strain_id", "mamey_version", "workflow_version", "mode",
                "chatgpt_safe", "process", "phases"}
    assert required.issubset(set(data.keys()))
    assert data["strain_id"] == "STRAIN1"
    assert data["chatgpt_safe"] is True
    assert len(data["phases"]) == 1
    assert data["phases"][0]["name"] == "antismash_kcb_riq_parse"
    proc = data["process"]
    assert "start_utc" in proc and "elapsed_seconds" in proc


def test_csv_has_all_phases(tmp_path):
    """timing CSV must have one row per phase."""
    rec = TimingRecorder("S2", "standard", "1.9.84")
    phase_names = ["antismash_kcb_riq_parse", "bgc_region_inventory_parse",
                   "source_scans_cctt_cgad_efls_resistance_tfbs"]
    for name in phase_names:
        with rec.phase(name):
            pass
    rec.write(tmp_path)
    rows = list(csv.DictReader(open(tmp_path / "S2_timing_breakdown.csv")))
    assert len(rows) == len(phase_names)
    assert [r["name"] for r in rows] == phase_names
    assert all(r["status"] == "PASS" for r in rows)


def test_manifest_pointer(tmp_path):
    """manifest_pointer() returns expected keys."""
    rec = TimingRecorder("S3", "smoke", "1.9.84")
    ptr = rec.manifest_pointer("S3")
    assert ptr["timing_json"] == "S3_timing_breakdown.json"
    assert ptr["timing_csv"] == "S3_timing_breakdown.csv"
    assert ptr["timing_md"] == "S3_timing_breakdown.md"
    assert ptr["canonical_clock"] == "time.monotonic_ns"


def test_record_pretimed_phase(tmp_path):
    """record() registers a pre-timed phase correctly."""
    rec = TimingRecorder("S4", "smoke", "1.9.84")
    rec.record("manual_phase", elapsed_seconds=3.14, status="PASS",
               notes="externally timed")
    data = rec.finish()
    assert len(data["phases"]) == 1
    p = data["phases"][0]
    assert p["name"] == "manual_phase"
    assert abs(p["elapsed_seconds"] - 3.14) < 0.01
    assert p["status"] == "PASS"
