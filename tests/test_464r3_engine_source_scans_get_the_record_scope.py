# Synthetic regression inputs only.
"""A run binds the GenBank record set to the FLBR and UMED counts.

`parsers.genbank_record_scope` (round-3 card r3e 03) says whether the readers used whole-record
GenBank or region records only, and `run_source_scans(..., record_scope=...)` stamps it as
`count_scope`. The run did not pass it, so every real package read `NOT_BOUND`.
"""
from __future__ import annotations

import pytest

import mamey.cli as cli

parsers = pytest.importorskip("mamey.parsers")
if not hasattr(parsers, "genbank_record_scope"):
    pytest.skip("needs round-3 card r3e 03 (parsers.genbank_record_scope)", allow_module_level=True)


def test_run_passes_the_archive_record_scope_to_the_source_scans(tmp_path, monkeypatch,
                                                                  synthetic_single_contig_admitted_zip):
    seen = {}
    real = cli.run_source_scans

    def spy(*args, **kwargs):
        seen.update(kwargs)
        seen["result"] = real(*args, **kwargs)
        return seen["result"]

    monkeypatch.setattr(cli, "run_source_scans", spy)
    cli.run_one_strain(strain_id="SYNTHETIC-SCOPE", display_name="SYNTHETIC-SCOPE",
                       input_zip=str(synthetic_single_contig_admitted_zip), outdir=str(tmp_path),
                       mode="full", taxonomy="", source="", bioactivity="", master_path=None,
                       json_mode="off")
    expected = parsers.genbank_record_scope(str(synthetic_single_contig_admitted_zip))
    assert seen.get("record_scope") == expected
    assert expected["state"] != "NOT_BOUND"
    for scan in ("flbr", "umed"):
        block = getattr(seen["result"], scan) or {}
        assert block.get("count_scope", {}).get("state") == expected["state"], scan
