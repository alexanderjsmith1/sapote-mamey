"""The manifest keeps the archive's own antiSMASH strictness beside the profile the run used.

An explicit `--antismash-profile` was written to `manifest.json` as `antismash_profile` even when
the archive recorded another strictness or none, so the manifest value alone looked like
evidence of the archive's strictness.
"""
import json

import pytest

import mamey.cli as cli


@pytest.mark.parametrize("requested", ["auto", "strict"])
def test_manifest_records_requested_used_and_archive_profile(tmp_path, requested,
                                                             synthetic_single_contig_full_locus_zip):
    strain = "SYNPROF" + requested.upper()
    cli.run_one_strain(
        strain_id=strain, display_name=strain,
        input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(tmp_path), mode="full",
        taxonomy="", source="", bioactivity="", master_path=None, json_mode="off",
        antismash_profile=requested,
    )
    pkg = tmp_path / strain / "package"
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["antismash_profile_record"]
    assert record["requested"] == requested
    assert record["used"] == manifest["antismash_profile"]
    assert record["archive_recorded"]
    if record["archive_recorded"] == "unknown":
        assert record["state"] == "ARCHIVE_UNREADABLE"
    elif requested == "auto":
        assert record["state"] == "READ_FROM_ARCHIVE"
    else:
        assert record["state"] in {"MATCHES_ARCHIVE", "MISMATCH_ARCHIVE_DIFFERS"}
    intake = json.loads(next(pkg.glob("*_1_intake.json")).read_text(encoding="utf-8"))
    assert intake["antismash_profile_record"] == record
